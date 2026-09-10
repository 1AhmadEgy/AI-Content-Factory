from __future__ import annotations

import json

from ..domain.content import ContentBrief, StoryPlan
from ..providers.contracts import ProviderRequest
from ..providers.registry import ModelRegistry


class AIScriptEngine:
    """Turns a structured story into production-ready scene scripts."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def generate(self, brief: ContentBrief, story: StoryPlan, model_id: str | None = None) -> StoryPlan:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "script")
        if model is None:
            return story
        prompt = (
            "Rewrite this structured story into production-ready scene scripts. "
            "Return strict JSON with title, logline, synopsis and scenes. Preserve scene count, "
            "durations and shots while improving narration, visual direction and shot prompts. "
            f"Language: {brief.language}. Story: {json.dumps(_to_dict(story), ensure_ascii=False)}"
        )
        response = model.adapter.execute(ProviderRequest(model=model.id, parameters={"prompt": prompt}))
        if not response.success or not response.output_text:
            return story
        try:
            return _story_from_dict(json.loads(response.output_text))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return story


def _to_dict(story: StoryPlan) -> dict[str, object]:
    return {
        "title": story.title,
        "logline": story.logline,
        "synopsis": story.synopsis,
        "scenes": [
            {
                "number": scene.number,
                "title": scene.title,
                "duration_seconds": scene.duration_seconds,
                "visual": scene.visual,
                "narration": scene.narration,
                "shots": [
                    {
                        "number": shot.number,
                        "prompt": shot.prompt,
                        "duration_seconds": shot.duration_seconds,
                        "camera": shot.camera,
                        "lighting": shot.lighting,
                        "style": shot.style,
                    }
                    for shot in scene.shots
                ],
            }
            for scene in story.scenes
        ],
    }


def _story_from_dict(data: dict[str, object]) -> StoryPlan:
    from ..domain.content import ScenePlan, ShotPlan

    scenes = []
    for raw in data["scenes"]:
        scene = dict(raw)
        scene["shots"] = tuple(ShotPlan(**dict(shot)) for shot in scene.get("shots", []))
        scenes.append(ScenePlan(**scene))
    return StoryPlan(str(data["title"]), str(data["logline"]), str(data["synopsis"]), tuple(scenes))
