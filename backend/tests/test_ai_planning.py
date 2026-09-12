from __future__ import annotations

import json

from app.application.ai_scene_planner import AIScenePlanner
from app.application.ai_story_engine import AIStoryEngine
from app.domain.content import ContentBrief, ScenePlan, ShotPlan, StoryPlan
from app.providers.contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse
from app.providers.registry import ModelRegistry, RegisteredModel


class StubAdapter(ModelAdapter):
    """Test-only transport stub; no production mock provider is exposed."""
    def __init__(self, response_text: str = "") -> None: self.response_text = response_text
    def capability(self) -> ModelCapability: return ModelCapability("generation", frozenset({"story", "scene", "shot", "text"}), runtime="TEST", license_status="OPEN")
    def health_check(self) -> bool: return True
    def execute(self, request: ProviderRequest) -> ProviderResponse: return ProviderResponse(True, output_text=self.response_text, provider_run_id="test-run")
    def cancel(self, provider_run_id: str) -> bool: return False


def _registry(response_text: str = "") -> ModelRegistry:
    registry = ModelRegistry(); registry.register(RegisteredModel("test-model", "test", StubAdapter(response_text), priority=1)); return registry


def _story() -> StoryPlan:
    return StoryPlan("Title", "Logline", "Synopsis", (ScenePlan(1, "Scene", 10, "Visual", "Narration", (ShotPlan(1, "prompt", 10),)),))


def test_story_engine_accepts_valid_provider_response() -> None:
    payload = json.dumps({"title": "Generated", "logline": "A logline", "synopsis": "A synopsis", "scenes": [{"number": 1, "title": "Scene 1", "duration_seconds": 10, "visual": "Space", "narration": "Stars", "shots": [{"number": 1, "prompt": "stars", "duration_seconds": 10, "camera": "medium", "lighting": "natural", "style": "cinematic", "character_ids": [], "location_ids": []}]}]})
    result = AIStoryEngine(_registry(payload)).generate(ContentBrief("space"), "test-model")
    assert result.title == "Generated"
    assert result.scenes[0].shots


def test_story_engine_rejects_empty_scene_list() -> None:
    payload = json.dumps({"title": "Generated", "logline": "A logline", "synopsis": "A synopsis", "scenes": []})
    try:
        AIStoryEngine(_registry(payload)).generate(ContentBrief("space"), "test-model")
    except RuntimeError as exc:
        assert str(exc).startswith("AI_STORY_SCHEMA_INVALID")
    else:
        raise AssertionError("invalid story schema must fail")


def test_scene_planner_updates_scene_direction_from_provider_json() -> None:
    class SceneAdapter(StubAdapter):
        def execute(self, request: ProviderRequest) -> ProviderResponse:
            if "JSON array" in request.parameters["prompt"]:
                return ProviderResponse(True, output_text=json.dumps([{"number": 1, "prompt": "a precise cinematic shot", "duration_seconds": 99, "camera": "wide", "lighting": "soft", "style": "realistic"}]), provider_run_id="test-scene")
            return ProviderResponse(True, output_text=json.dumps({"scenes": [{"title": "Improved", "visual": "Detailed visual", "narration": "Natural narration"}]}), provider_run_id="test-edit")
    registry = ModelRegistry(); registry.register(RegisteredModel("editor", "test", SceneAdapter(), priority=1))
    planner = AIScenePlanner(registry); brief = ContentBrief("test"); edited = planner.plan(brief, _story(), "editor")
    assert edited.scenes[0].title == "Improved"
    shots = planner.plan_shots(brief, edited.scenes[0], "editor")
    assert shots[0].prompt == "a precise cinematic shot"; assert shots[0].duration_seconds == 10
