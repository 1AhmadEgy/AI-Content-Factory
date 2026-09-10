from __future__ import annotations

import json

from ..domain.content import ContentBrief, ScenePlan, ShotPlan, StoryPlan
from ..providers.contracts import ProviderRequest
from ..providers.registry import ModelRegistry
from .ai_json import parse_json_object
from .content_planner import DeterministicContentPlanner


class AIStoryEngine:
    """AI-first story engine with deterministic fallback for offline operation."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        self.fallback = DeterministicContentPlanner()

    def generate(self, brief: ContentBrief, model_id: str | None = None) -> StoryPlan:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "story")
        if model is None:
            return self.fallback.plan(brief)
        prompt = _story_prompt(brief)
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


def _story_prompt(brief: ContentBrief) -> str:
    return (
        "You are the story director for an automated video production system. "
        "Return ONLY valid JSON. Create a coherent, original, production-ready story. "
        "Required keys: title, logline, synopsis, scenes. Each scene requires number,title,"
        "duration_seconds,visual,narration,shots. Each shot requires number,prompt,duration_seconds,"
        "camera,lighting,style. Keep total scene duration close to the requested duration. "
        f"Language={brief.language}; Duration={brief.duration_seconds}s; Style={brief.style}; "
        f"Audience={brief.audience}; Platform={brief.platform}; AspectRatio={brief.aspect_ratio}; Topic={brief.topic}"
    )


def _story_from_dict(data: dict[str, object]) -> StoryPlan:
    title = str(data["title"]).strip()
    logline = str(data["logline"]).strip()
    synopsis = str(data["synopsis"]).strip()
    raw_scenes = data["scenes"]
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise ValueError("scenes must be a non-empty list")
    scenes: list[ScenePlan] = []
    for raw_scene in raw_scenes:
        if not isinstance(raw_scene, dict):
            raise TypeError("invalid scene")
        raw_shots = raw_scene.get("shots", [])
        if not isinstance(raw_shots, list):
            raise TypeError("invalid shots")
        shots = tuple(ShotPlan(**dict(shot)) for shot in raw_shots if isinstance(shot, dict))
        if not shots:
            raise ValueError("scene has no shots")
        scene = dict(raw_scene)
        scene["shots"] = shots
        scenes.append(ScenePlan(**scene))
    return StoryPlan(title=title, logline=logline, synopsis=synopsis, scenes=tuple(scenes))
