from __future__ import annotations

import json

from ..domain.content import ContentBrief, ShotPlan, ScenePlan, StoryPlan
from ..providers.contracts import ProviderRequest
from ..providers.registry import ModelRegistry
from .ai_json import parse_json_object


class AIScriptEngine:
    """Turns a structured story into production-ready scene scripts.

    A missing/unhealthy provider is a hard failure. The engine never silently
    substitutes the input story and therefore cannot report an AI edit that did
    not actually happen.
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def generate(self, brief: ContentBrief, story: StoryPlan, model_id: str | None = None) -> StoryPlan:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "script")
        if model is None:
            raise RuntimeError("AI_PROVIDER_UNAVAILABLE: no script-capable provider is configured")

        prompt = (
            "You are a production script editor. Return ONLY valid JSON with title, logline, synopsis and scenes. "
            "Preserve scene count, scene durations and shot count. Improve narration so it sounds natural when voiced, "
            "and make visuals and shot prompts concrete and generatable. Keep the requested language. "
            f"Language={brief.language}; Duration={brief.duration_seconds}s; Audience={brief.audience}; "
            f"Platform={brief.platform}; Story={json.dumps(_to_dict(story), ensure_ascii=False)}"
        )
        response = model.adapter.execute(
            ProviderRequest(model=model.id, parameters={"prompt": prompt, "temperature": 0.65, "response_format": "json"})
        )
        if not response.success or not response.output_text:
            raise RuntimeError(f"AI_SCRIPT_GENERATION_FAILED: {response.error_code or 'EMPTY_RESPONSE'}")

        data = parse_json_object(response.output_text)
        if data is None:
            raise RuntimeError("AI_SCRIPT_GENERATION_FAILED: INVALID_JSON")
        try:
            candidate = _story_from_dict(data)
            return _normalize_to_story(candidate, story)
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"AI_SCRIPT_GENERATION_FAILED: INVALID_SCHEMA: {exc}") from exc


def _to_dict(story: StoryPlan) -> dict[str, object]:
    return {
        "title": story.title,
        "logline": story.logline,
        "synopsis": story.synopsis,
        "scenes": [_scene_dict(scene) for scene in story.scenes],
    }


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
            }
            for s in scene.shots
        ],
    }


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
        shots = tuple(ShotPlan(**dict(shot)) for shot in raw_shots if isinstance(shot, dict))
        if not shots:
            raise ValueError("scene has no shots")
        item = dict(raw)
        item["shots"] = shots
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
        shots = tuple(
            ShotPlan(
                number=base_shot.number,
                prompt=edited_shot.prompt or base_shot.prompt,
                duration_seconds=base_shot.duration_seconds,
                camera=edited_shot.camera or base_shot.camera,
                lighting=edited_shot.lighting or base_shot.lighting,
                style=edited_shot.style or base_shot.style,
            )
            for base_shot, edited_shot in zip(base.shots, edited.shots)
        )
        scenes.append(
            ScenePlan(
                base.number,
                edited.title or base.title,
                base.duration_seconds,
                edited.visual or base.visual,
                edited.narration or base.narration,
                shots,
            )
        )
    return StoryPlan(
        candidate.title or original.title,
        candidate.logline or original.logline,
        candidate.synopsis or original.synopsis,
        tuple(scenes),
    )
