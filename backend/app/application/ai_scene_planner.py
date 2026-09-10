from __future__ import annotations

import json

from ..domain.content import ContentBrief, ScenePlan, ShotPlan, StoryPlan
from ..providers.contracts import ProviderRequest
from ..providers.registry import ModelRegistry
from .ai_json import parse_json_array, parse_json_object


class AIScenePlanner:
    """Produces normalized scene and shot direction through the model registry."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def plan(self, brief: ContentBrief, story: StoryPlan, model_id: str | None = None) -> StoryPlan:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "scene")
        if model is None:
            return story
        payload = _story_dict(story)
        prompt = (
            "Act as a professional scene director. Return ONLY valid JSON with a scenes array. "
            "Improve scene titles, visual direction and narration while preserving scene numbers, "
            "durations and shot counts. Keep the language consistent. "
            f"Language={brief.language}; Style={brief.style}; AspectRatio={brief.aspect_ratio}; "
            f"Story={json.dumps(payload, ensure_ascii=False)}"
        )
        response = model.adapter.execute(ProviderRequest(model=model.id, parameters={"prompt": prompt, "temperature": 0.5}))
        if not response.success or not response.output_text:
            return story
        data = parse_json_object(response.output_text)
        if data is None or not isinstance(data.get("scenes"), list):
            return story
        try:
            scenes: list[ScenePlan] = []
            for raw in data["scenes"]:
                if not isinstance(raw, dict):
                    return story
                base = story.scenes[len(scenes)] if len(scenes) < len(story.scenes) else None
                if base is None:
                    return story
                scenes.append(ScenePlan(
                    number=base.number,
                    title=str(raw.get("title", base.title)),
                    duration_seconds=base.duration_seconds,
                    visual=str(raw.get("visual", base.visual)),
                    narration=str(raw.get("narration", base.narration)),
                    shots=base.shots,
                ))
            return StoryPlan(story.title, story.logline, story.synopsis, tuple(scenes)) if len(scenes) == len(story.scenes) else story
        except (TypeError, ValueError):
            return story

    def plan_shots(self, brief: ContentBrief, scene: ScenePlan, model_id: str | None = None) -> tuple[ShotPlan, ...]:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "shot")
        if model is None:
            return scene.shots
        prompt = (
            "Act as a cinematographer. Return ONLY a JSON array. Improve every shot prompt for "
            "visual generation. Preserve shot numbers and durations. Include number,prompt,"
            "duration_seconds,camera,lighting,style. "
            f"Language={brief.language}; AspectRatio={brief.aspect_ratio}; Scene={json.dumps(_scene_dict(scene), ensure_ascii=False)}"
        )
        response = model.adapter.execute(ProviderRequest(model=model.id, parameters={"prompt": prompt, "temperature": 0.6}))
        if not response.success or not response.output_text:
            return scene.shots
        raw_shots = parse_json_array(response.output_text)
        if raw_shots is None or len(raw_shots) != len(scene.shots):
            return scene.shots
        try:
            result: list[ShotPlan] = []
            for index, raw in enumerate(raw_shots):
                if not isinstance(raw, dict):
                    return scene.shots
                base = scene.shots[index]
                result.append(ShotPlan(
                    number=base.number,
                    prompt=str(raw.get("prompt", base.prompt)),
                    duration_seconds=base.duration_seconds,
                    camera=str(raw.get("camera", base.camera)),
                    lighting=str(raw.get("lighting", base.lighting)),
                    style=str(raw.get("style", base.style)),
                ))
            return tuple(result)
        except (TypeError, ValueError):
            return scene.shots


def _scene_dict(scene: ScenePlan) -> dict[str, object]:
    return {
        "number": scene.number,
        "title": scene.title,
        "duration_seconds": scene.duration_seconds,
        "visual": scene.visual,
        "narration": scene.narration,
        "shots": [
            {"number": s.number, "prompt": s.prompt, "duration_seconds": s.duration_seconds, "camera": s.camera, "lighting": s.lighting, "style": s.style}
            for s in scene.shots
        ],
    }


def _story_dict(story: StoryPlan) -> dict[str, object]:
    return {
        "title": story.title,
        "logline": story.logline,
        "synopsis": story.synopsis,
        "scenes": [_scene_dict(scene) for scene in story.scenes],
    }
