from __future__ import annotations

import json

from ..domain.content import ContentBrief, ScenePlan, ShotPlan, StoryPlan
from ..providers.contracts import ProviderRequest
from ..providers.registry import ModelRegistry
from .ai_json import parse_json_array, parse_json_object


class AIScenePlanner:
    """AI scene and shot planner with strict schema preservation."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def plan(self, brief: ContentBrief, story: StoryPlan, model_id: str | None = None) -> StoryPlan:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "scene")
        if model is None:
            return story
        prompt = ("Act as a professional scene director. Return ONLY valid JSON with a scenes array. "
                  "Improve scene titles, visual direction and narration while preserving scene numbers, durations and shot counts. "
                  f"Language={brief.language}; Style={brief.style}; AspectRatio={brief.aspect_ratio}; Story={json.dumps(_story_dict(story), ensure_ascii=False)}")
        response = model.adapter.execute(ProviderRequest(model=model.id, parameters={"prompt": prompt, "temperature": 0.5, "response_format": "json"}))
        if not response.success or not response.output_text:
            return story
        data = parse_json_object(response.output_text)
        if data is None or not isinstance(data.get("scenes"), list) or len(data["scenes"]) != len(story.scenes):
            return story
        scenes: list[ScenePlan] = []
        for index, raw in enumerate(data["scenes"]):
            if not isinstance(raw, dict):
                return story
            base = story.scenes[index]
            scenes.append(ScenePlan(base.number, str(raw.get("title", base.title)), base.duration_seconds, str(raw.get("visual", base.visual)), str(raw.get("narration", base.narration)), base.shots))
        return StoryPlan(str(data.get("title", story.title)), str(data.get("logline", story.logline)), str(data.get("synopsis", story.synopsis)), tuple(scenes))

    def plan_shots(self, brief: ContentBrief, scene: ScenePlan, model_id: str | None = None) -> tuple[ShotPlan, ...]:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "shot")
        if model is None or not scene.shots:
            return scene.shots
        prompt = ("Act as a cinematographer. Return ONLY a JSON array. Improve every shot prompt for visual generation. "
                  "Preserve shot numbers and durations. Include number,prompt,duration_seconds,camera,lighting,style. "
                  f"Language={brief.language}; AspectRatio={brief.aspect_ratio}; Scene={json.dumps(_scene_dict(scene), ensure_ascii=False)}")
        response = model.adapter.execute(ProviderRequest(model=model.id, parameters={"prompt": prompt, "temperature": 0.6, "response_format": "json"}))
        if not response.success or not response.output_text:
            return scene.shots
        raw_shots = parse_json_array(response.output_text)
        if raw_shots is None or len(raw_shots) != len(scene.shots):
            return scene.shots
        result: list[ShotPlan] = []
        for index, raw in enumerate(raw_shots):
            if not isinstance(raw, dict):
                return scene.shots
            base = scene.shots[index]
            result.append(ShotPlan(base.number, str(raw.get("prompt", base.prompt)), base.duration_seconds, str(raw.get("camera", base.camera)), str(raw.get("lighting", base.lighting)), str(raw.get("style", base.style))))
        return tuple(result)


def _scene_dict(scene: ScenePlan) -> dict[str, object]:
    return {"number": scene.number, "title": scene.title, "duration_seconds": scene.duration_seconds, "visual": scene.visual, "narration": scene.narration, "shots": [{"number": s.number, "prompt": s.prompt, "duration_seconds": s.duration_seconds, "camera": s.camera, "lighting": s.lighting, "style": s.style} for s in scene.shots]}


def _story_dict(story: StoryPlan) -> dict[str, object]:
    return {"title": story.title, "logline": story.logline, "synopsis": story.synopsis, "scenes": [_scene_dict(scene) for scene in story.scenes]}
