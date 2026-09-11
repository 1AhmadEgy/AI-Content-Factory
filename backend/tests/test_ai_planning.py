from __future__ import annotations

import json

from app.application.ai_scene_planner import AIScenePlanner
from app.application.ai_story_engine import AIStoryEngine
from app.domain.content import ContentBrief, ScenePlan, ShotPlan, StoryPlan
from app.providers.contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse
from app.providers.registry import ModelRegistry, RegisteredModel


class TestAdapter(ModelAdapter):
    """Test-only transport stub; no production mock provider is exposed."""

    def __init__(self, response_text: str = "") -> None:
        self.response_text = response_text

    def capability(self) -> ModelCapability:
        return ModelCapability("generation", frozenset({"story", "scene", "shot", "text"}), runtime="TEST", license_status="OPEN")

    def health_check(self) -> bool:
        return True

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(True, output_text=self.response_text, provider_run_id="test-run")

    def cancel(self, provider_run_id: str) -> bool:
        return False


def _registry(response_text: str = "") -> ModelRegistry:
    registry = ModelRegistry()
    registry.register(RegisteredModel("test-model", "test", TestAdapter(response_text), priority=1))
    return registry


def _story() -> StoryPlan:
    return StoryPlan(
        "Title", "Logline", "Synopsis",
        (ScenePlan(1, "Scene", 10, "Visual", "Narration", (ShotPlan(1, "prompt", 10),)),),
    )


def test_story_engine_accepts_real_provider_response() -> None:
    payload = json.dumps({"title": "Generated", "logline": "A logline", "synopsis": "A synopsis", "scenes": []})
    engine = AIStoryEngine(_registry(payload))
    result = engine.generate(ContentBrief("space"), "test-model")
    assert result.title == "Generated"


def test_scene_planner_updates_scene_direction_from_provider_json() -> None:
    class SceneAdapter(TestAdapter):
        def execute(self, request: ProviderRequest) -> ProviderResponse:
            if "JSON array" in request.parameters["prompt"]:
                return ProviderResponse(True, output_text=json.dumps([{
                    "number": 1, "prompt": "a precise cinematic shot", "duration_seconds": 99,
                    "camera": "wide", "lighting": "soft", "style": "realistic"
                }]), provider_run_id="test-scene")
            return ProviderResponse(True, output_text=json.dumps({"scenes": [{
                "title": "Improved", "visual": "Detailed visual", "narration": "Natural narration"
            }]}), provider_run_id="test-edit")

    registry = ModelRegistry()
    registry.register(RegisteredModel("editor", "test", SceneAdapter(), priority=1))
    planner = AIScenePlanner(registry)
    brief = ContentBrief("test")
    story = _story()
    edited = planner.plan(brief, story, "editor")
    assert edited.scenes[0].title == "Improved"
    shots = planner.plan_shots(brief, edited.scenes[0], "editor")
    assert shots[0].prompt == "a precise cinematic shot"
    assert shots[0].duration_seconds == 10
