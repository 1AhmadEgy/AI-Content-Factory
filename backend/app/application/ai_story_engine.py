from __future__ import annotations

from ..domain.content import ContentBrief, ScenePlan, ShotPlan, StoryPlan
from ..domain.characters import CharacterProfile
from ..providers.contracts import ProviderRequest
from ..providers.registry import ModelRegistry
from .ai_json import parse_json_object
from .content_planner import DeterministicContentPlanner


class AIStoryEngine:
    """AI-first story director. Reused character profiles become immutable continuity context."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        self.fallback = DeterministicContentPlanner()

    def generate(self, brief: ContentBrief, model_id: str | None = None,
                 characters: tuple[CharacterProfile, ...] = ()) -> StoryPlan:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "story")
        if model is None:
            return self.fallback.plan(brief)
        prompt = _story_prompt(brief, characters)
        response = model.adapter.execute(ProviderRequest(model=model.id, parameters={"prompt": prompt, "temperature": 0.7}))
        if not response.success or not response.output_text:
            return self.fallback.plan(brief)
        data = parse_json_object(response.output_text)
        if data is None:
            return self.fallback.plan(brief)
        try:
            return _story_from_dict(data)
        except (KeyError, TypeError, ValueError):
            return self.fallback.plan(brief)


def _story_prompt(brief: ContentBrief, characters: tuple[CharacterProfile, ...]) -> str:
    character_context = "\n".join(
        f"CHARACTER {c.id}: name={c.name}; personality={c.personality}; appearance={c.appearance}; "
        f"voice={c.voice}; speakingStyle={c.speaking_style}; visualStyle={c.visual_style}; "
        f"behaviorRules={list(c.behavior_rules)}; references={list(c.reference_asset_ids)}"
        for c in characters
    ) or "No saved characters."
    continuity = "; ".join(brief.continuity_rules) or "Preserve identity, voice, appearance and behavior across every scene."
    return (
        "You are the story director for an automated video production system. Return ONLY valid JSON. "
        "Create a coherent production-ready story. Reuse the supplied saved characters exactly; never redesign "
        "their face, body, clothing identity, voice, personality or speaking manner unless explicitly requested. "
        "Required keys: title, logline, synopsis, scenes. Each scene requires number,title,duration_seconds,visual,"
        "narration,shots. Each shot requires number,prompt,duration_seconds,camera,lighting,style,character_ids. "
        f"Language={brief.language}; Duration={brief.duration_seconds}s; Style={brief.style}; Audience={brief.audience}; "
        f"Platform={brief.platform}; AspectRatio={brief.aspect_ratio}; Topic={brief.topic}; Continuity={continuity}\n"
        f"SAVED CHARACTERS:\n{character_context}"
    )


def _story_from_dict(data: dict[str, object]) -> StoryPlan:
    title, logline, synopsis = str(data["title"]).strip(), str(data["logline"]).strip(), str(data["synopsis"]).strip()
    raw_scenes = data["scenes"]
    if not isinstance(raw_scenes, list) or not raw_scenes: raise ValueError("scenes must be a non-empty list")
    scenes: list[ScenePlan] = []
    for raw_scene in raw_scenes:
        if not isinstance(raw_scene, dict): raise TypeError("invalid scene")
        raw_shots = raw_scene.get("shots", [])
        if not isinstance(raw_shots, list): raise TypeError("invalid shots")
        normalized_shots = []
        for shot in raw_shots:
            if isinstance(shot, dict):
                item = dict(shot)
                item["character_ids"] = tuple(item.get("character_ids", item.get("characterIds", [])))
                item.pop("characterIds", None)
                normalized_shots.append(ShotPlan(**item))
        if not normalized_shots: raise ValueError("scene has no shots")
        scene = dict(raw_scene); scene["shots"] = tuple(normalized_shots)
        scenes.append(ScenePlan(**scene))
    return StoryPlan(title=title, logline=logline, synopsis=synopsis, scenes=tuple(scenes))
