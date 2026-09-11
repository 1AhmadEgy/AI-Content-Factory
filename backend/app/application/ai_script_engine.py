from __future__ import annotations

import json

from ..domain.content import ContentBrief, ScenePlan, ShotPlan, StoryPlan
from ..providers.contracts import ProviderRequest
from ..providers.registry import ModelRegistry
from .ai_json import parse_json_object


class AIScriptEngine:
    """Production script editor; provider failures are explicit and identity continuity is immutable."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def generate(self, brief: ContentBrief, story: StoryPlan, model_id: str | None = None) -> StoryPlan:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "script")
        if model is None:
            raise RuntimeError("AI_PROVIDER_NOT_CONFIGURED:script")
        prompt = (
            "You are a production script editor. Return ONLY valid JSON with title, logline, synopsis and scenes. "
            "Preserve scene count, scene durations, shot count, character_ids and location_ids exactly. "
            "Do not create, rename, remove, substitute, or invent people or places. The supplied identity IDs are canonical "
            "and must be copied unchanged into the corresponding shots. Improve narration so it sounds natural when voiced, "
            "and make visuals and shot prompts concrete and generatable. Keep the requested language. "
            f"CountryId={brief.country_id}; LibraryId={brief.library_id}; Language={brief.language}; Duration={brief.duration_seconds}s; "
            f"Audience={brief.audience}; Platform={brief.platform}; Continuity={'; '.join(brief.continuity_rules) or 'Preserve all supplied identity and location continuity.'}; "
            f"ProductionContext={json.dumps(brief.production_context, ensure_ascii=False)}; Story={json.dumps(_to_dict(story), ensure_ascii=False)}"
        )
        response = model.adapter.execute(ProviderRequest(model=model.id, parameters={"prompt": prompt, "temperature": 0.65, "response_format": "json"}))
        if not response.success or not response.output_text:
            raise RuntimeError(response.error_code or "AI_PROVIDER_FAILED:script")
        data = parse_json_object(response.output_text)
        if data is None:
            raise RuntimeError("AI_PROVIDER_INVALID_JSON:script")
        try:
            candidate = _story_from_dict(data)
            return _normalize_to_story(candidate, story)
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"AI_PROVIDER_INVALID_SCRIPT:{exc}") from exc


def _to_dict(story: StoryPlan) -> dict[str, object]:
    return {"title": story.title, "logline": story.logline, "synopsis": story.synopsis, "scenes": [_scene_dict(scene) for scene in story.scenes]}


def _scene_dict(scene: ScenePlan) -> dict[str, object]:
    return {"number": scene.number, "title": scene.title, "duration_seconds": scene.duration_seconds, "visual": scene.visual, "narration": scene.narration, "shots": [{"number": s.number, "prompt": s.prompt, "duration_seconds": s.duration_seconds, "camera": s.camera, "lighting": s.lighting, "style": s.style, "character_ids": list(s.character_ids), "location_ids": list(s.location_ids)} for s in scene.shots]}


def _story_from_dict(data: dict[str, object]) -> StoryPlan:
    raw_scenes = data["scenes"]
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise ValueError("invalid scenes")
    scenes: list[ScenePlan] = []
    for raw in raw_scenes:
        if not isinstance(raw, dict):
            raise TypeError("invalid scene")
        raw_shots = raw.get("shots", [])
        if not isinstance(raw_shots, list):
            raise TypeError("invalid shots")
        shots: list[ShotPlan] = []
        for shot in raw_shots:
            if not isinstance(shot, dict):
                continue
            item = dict(shot)
            item["character_ids"] = tuple(item.get("character_ids", item.get("characterIds", [])))
            item["location_ids"] = tuple(item.get("location_ids", item.get("locationIds", [])))
            item.pop("characterIds", None)
            item.pop("locationIds", None)
            shots.append(ShotPlan(**item))
        if not shots:
            raise ValueError("scene has no shots")
        item = dict(raw)
        item["shots"] = tuple(shots)
        scenes.append(ScenePlan(**item))
    return StoryPlan(str(data["title"]), str(data["logline"]), str(data["synopsis"]), tuple(scenes))


def _normalize_to_story(candidate: StoryPlan, original: StoryPlan) -> StoryPlan:
    if len(candidate.scenes) != len(original.scenes):
        raise ValueError("provider changed scene count")
    scenes: list[ScenePlan] = []
    for index, base in enumerate(original.scenes):
        edited = candidate.scenes[index]
        if len(edited.shots) != len(base.shots):
            raise ValueError("provider changed shot count")
        shots = []
        for base_shot, edited_shot in zip(base.shots, edited.shots):
            if tuple(edited_shot.character_ids) != tuple(base_shot.character_ids) or tuple(edited_shot.location_ids) != tuple(base_shot.location_ids):
                raise ValueError("provider changed canonical character/location IDs")
            shots.append(ShotPlan(
                number=base_shot.number,
                prompt=edited_shot.prompt or base_shot.prompt,
                duration_seconds=base_shot.duration_seconds,
                camera=edited_shot.camera or base_shot.camera,
                lighting=edited_shot.lighting or base_shot.lighting,
                style=edited_shot.style or base_shot.style,
                character_ids=base_shot.character_ids,
                location_ids=base_shot.location_ids,
            ))
        scenes.append(ScenePlan(base.number, edited.title or base.title, base.duration_seconds, edited.visual or base.visual, edited.narration or base.narration, tuple(shots)))
    return StoryPlan(candidate.title or original.title, candidate.logline or original.logline, candidate.synopsis or original.synopsis, tuple(scenes))
