from __future__ import annotations

import json

from app.application.ai_scene_planner import AIScenePlanner
from app.application.ai_story_engine import AIStoryEngine
from app.domain.content import ContentBrief, ScenePlan, ShotPlan, StoryPlan
from app.providers.builtin import MockModelAdapter
from app.providers.contracts import ModelCapability, ProviderResponse
from app.providers.registry import ModelRegistry, RegisteredModel


def _registry() -> ModelRegistry:
    registry = ModelRegistry()
    registry.register(RegisteredModel("test-model", "test", MockModelAdapter(), priority=1))
    return registry


def _story() -> StoryPlan:
    return StoryPlan(
        "Title", "Logline", "Synopsis",
        (ScenePlan(1, "Scene", 10, "Visual", "Narration", (ShotPlan(1, "prompt", 10),)),),
    )


def test_story_engine_accepts_embedded_json_and_falls_back_on_invalid() -> None:
    engine = AIStoryEngine(_registry())
    result = engine.generate(ContentBrief("space"), "test-model")
    assert result.scenes
    assert result.scenes[0].shots


def test_scene_planner_updates_scene_direction_from_json() -> None:
    class Adapter(MockModelAdapter):
        @property
        def capability(self) -> ModelCapability:
            return ModelCapability("generation", ("scene", "shot"), runtime="MOCK", license_status="OPEN")

        def execute(self, request):
            if "JSON array" in request.parameters["prompt"]:
                return ProviderResponse(True, output_text=json.dumps([{
                    "number": 1, "prompt": "a precise cinematic shot", "duration_seconds": 99,
                    "camera": "wide", "lighting": "soft", "style": "realistic"
                }]))
            return ProviderResponse(True, output_text=json.dumps({"scenes": [{
                "title": "Improved", "visual": "Detailed visual", "narration": "Natural narration"
            }]}))

    registry = ModelRegistry()
    registry.register(RegisteredModel("editor", "test", Adapter(), priority=1))
    planner = AIScenePlanner(registry)
    brief = ContentBrief("test")
    story = _story()
    edited = planner.plan(brief, story, "editor")
    assert edited.scenes[0].title == "Improved"
    shots = planner.plan_shots(brief, edited.scenes[0], "editor")
    assert shots[0].prompt == "a precise cinematic shot"
    assert shots[0].duration_seconds == 10
