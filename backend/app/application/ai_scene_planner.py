from __future__ import annotations

import json

from ..domain.content import ContentBrief, ScenePlan, ShotPlan, StoryPlan
from ..providers.contracts import ProviderRequest
from ..providers.registry import ModelRegistry
from .ai_json import parse_json_array, parse_json_object


class AIScenePlanner:
    """Production scene and shot planner; provider failures are explicit and identities are immutable."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def plan(self, brief: ContentBrief, story: StoryPlan, model_id: str | None = None) -> StoryPlan:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "scene")
        if model is None:
            raise RuntimeError("AI_PROVIDER_NOT_CONFIGURED:scene")
        prompt = (
            "Act as a professional scene director. Return ONLY valid JSON with a scenes array. "
            "Improve scene titles, visual direction and narration while preserving scene numbers, durations, shot counts, "
            "and every canonical character_ids/location_ids exactly. Never create, rename, remove, substitute, or invent "
            "people or places. The supplied IDs are immutable production identities and must be copied unchanged. "
            "Use the supplied country/library/local context only; do not move the production to another country or location. "
            f"CountryId={brief.country_id}; LibraryId={brief.library_id}; Language={brief.language}; Dialect={brief.dialect or 'default'}; "
            f"Style={brief.style}; AspectRatio={brief.aspect_ratio}; Continuity={'; '.join(brief.continuity_rules) or 'Preserve all supplied identity and location continuity.'}; "
            f"ProductionContext={json.dumps(brief.production_context, ensure_ascii=False)}; Story={json.dumps(_story_dict(story), ensure_ascii=False)}"
        )
        response = model.adapter.execute(ProviderRequest(model=model.id, parameters={"prompt": prompt, "temperature": 0.5, "response_format": "json"}))
        if not response.success or not response.output_text:
            raise RuntimeError(response.error_code or "AI_PROVIDER_FAILED:scene")
        data = parse_json_object(response.output_text)
        if data is None or not isinstance(data.get("scenes"), list) or len(data["scenes"]) != len(story.scenes):
            raise RuntimeError("AI_PROVIDER_INVALID_SCENES:scene")
        scenes: list[ScenePlan] = []
        for index, raw in enumerate(data["scenes"]):
            if not isinstance(raw, dict):
                raise RuntimeError("AI_PROVIDER_INVALID_SCENE:scene")
            base = story.scenes[index]
            raw_shots = raw.get("shots")
            if raw_shots is not None and (not isinstance(raw_shots, list) or len(raw_shots) != len(base.shots)):
                raise RuntimeError("AI_PROVIDER_INVALID_SHOTS:scene shot count changed")
            scenes.append(
                ScenePlan(
                    base.number,
                    str(raw.get("title", base.title)),
                    base.duration_seconds,
                    str(raw.get("visual", base.visual)),
                    str(raw.get("narration", base.narration)),
                    base.shots,
                )
            )
        return StoryPlan(str(data.get("title", story.title)), str(data.get("logline", story.logline)), str(data.get("synopsis", story.synopsis)), tuple(scenes))

    def plan_shots(self, brief: ContentBrief, scene: ScenePlan, model_id: str | None = None) -> tuple[ShotPlan, ...]:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "shot")
        if model is None:
            raise RuntimeError("AI_PROVIDER_NOT_CONFIGURED:shot")
        if not scene.shots:
            raise RuntimeError("AI_PROVIDER_INVALID_SHOTS:empty scene")
        prompt = (
            "Act as a cinematographer. Return ONLY a JSON array. Improve every shot prompt for visual generation. "
            "Preserve shot numbers, durations, character_ids and location_ids exactly. Never create, rename, remove, "
            "substitute, or invent canonical people or places. Include number,prompt,duration_seconds,camera,lighting,style,"
            "character_ids,location_ids. Use the supplied country/library/local context only. "
            f"CountryId={brief.country_id}; LibraryId={brief.library_id}; Language={brief.language}; Dialect={brief.dialect or 'default'}; "
            f"AspectRatio={brief.aspect_ratio}; Continuity={'; '.join(brief.continuity_rules) or 'Preserve all supplied identity and location continuity.'}; "
            f"ProductionContext={json.dumps(brief.production_context, ensure_ascii=False)}; Scene={json.dumps(_scene_dict(scene), ensure_ascii=False)}"
        )
        response = model.adapter.execute(ProviderRequest(model=model.id, parameters={"prompt": prompt, "temperature": 0.6, "response_format": "json"}))
        if not response.success or not response.output_text:
            raise RuntimeError(response.error_code or "AI_PROVIDER_FAILED:shot")
        raw_shots = parse_json_array(response.output_text)
        if raw_shots is None or len(raw_shots) != len(scene.shots):
            raise RuntimeError("AI_PROVIDER_INVALID_SHOTS:shot count changed")
        result: list[ShotPlan] = []
        for index, raw in enumerate(raw_shots):
            if not isinstance(raw, dict):
                raise RuntimeError("AI_PROVIDER_INVALID_SHOT:shot")
            base = scene.shots[index]
            returned_characters = tuple(raw.get("character_ids", raw.get("characterIds", base.character_ids)))
            returned_locations = tuple(raw.get("location_ids", raw.get("locationIds", base.location_ids)))
            if returned_characters != base.character_ids or returned_locations != base.location_ids:
                raise RuntimeError("AI_PROVIDER_CONTINUITY_VIOLATION:shot canonical IDs changed")
            result.append(
                ShotPlan(
                    base.number,
                    str(raw.get("prompt", base.prompt)),
                    base.duration_seconds,
                    str(raw.get("camera", base.camera)),
                    str(raw.get("lighting", base.lighting)),
                    str(raw.get("style", base.style)),
                    base.character_ids,
                    base.location_ids,
                )
            )
        return tuple(result)


def _scene_dict(scene: ScenePlan) -> dict[str, object]:
    return {
        "number": scene.number,
        "title": scene.title,
        "duration_seconds": scene.duration_seconds,
        "visual": scene.visual,
        "narration": scene.narration,
        "shots": [
            {
                "number": s.number,
                "prompt": s.prompt,
                "duration_seconds": s.duration_seconds,
                "camera": s.camera,
                "lighting": s.lighting,
                "style": s.style,
                "character_ids": list(s.character_ids),
                "location_ids": list(s.location_ids),
            }
            for s in scene.shots
        ],
    }


def _story_dict(story: StoryPlan) -> dict[str, object]:
    return {"title": story.title, "logline": story.logline, "synopsis": story.synopsis, "scenes": [_scene_dict(scene) for scene in story.scenes]}
