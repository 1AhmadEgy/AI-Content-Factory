from __future__ import annotations

import json

import pytest

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


def _registry(response_text: str) -> ModelRegistry:
    registry = ModelRegistry()
    registry.register(RegisteredModel("test-model", "test", TestAdapter(response_text), priority=1))
    return registry


def _story() -> StoryPlan:
    return StoryPlan(
        "Title",
        "Logline",
        "Synopsis",
        (
            ScenePlan(
                1,
                "Scene",
                10,
                "Visual",
                "Narration",
                (ShotPlan(1, "prompt", 10, character_ids=("person-1",), location_ids=("place-1",)),),
            ),
        ),
    )


def test_story_engine_requires_configured_provider() -> None:
    with pytest.raises(RuntimeError, match="AI_PROVIDER_NOT_CONFIGURED:story"):
        AIStoryEngine(ModelRegistry()).generate(ContentBrief("space"))


def test_scene_planner_requires_configured_provider() -> None:
    with pytest.raises(RuntimeError, match="AI_PROVIDER_NOT_CONFIGURED:scene"):
        AIScenePlanner(ModelRegistry()).plan(ContentBrief("test"), _story())


def test_shot_planner_requires_configured_provider() -> None:
    with pytest.raises(RuntimeError, match="AI_PROVIDER_NOT_CONFIGURED:shot"):
        AIScenePlanner(ModelRegistry()).plan_shots(ContentBrief("test"), _story().scenes[0])


def test_scene_planner_preserves_canonical_ids_and_context() -> None:
    payload = json.dumps({
        "title": "Improved",
        "logline": "Updated",
        "synopsis": "Updated",
        "scenes": [{"title": "Improved Scene", "visual": "Detailed", "narration": "Natural"}],
    })
    planner = AIScenePlanner(_registry(payload))
    brief = ContentBrief("test", country_id="libya", library_id="libya-local", continuity_rules=("same people",))
    result = planner.plan(brief, _story(), "test-model")
    shot = result.scenes[0].shots[0]
    assert shot.character_ids == ("person-1",)
    assert shot.location_ids == ("place-1",)


def test_scene_planner_rejects_provider_shot_count_change() -> None:
    payload = json.dumps({
        "scenes": [{"title": "Changed", "shots": []}],
    })
    with pytest.raises(RuntimeError, match="AI_PROVIDER_INVALID_SHOTS:scene shot count changed"):
        AIScenePlanner(_registry(payload)).plan(ContentBrief("test"), _story(), "test-model")


def test_shot_planner_rejects_identity_substitution() -> None:
    payload = json.dumps([
        {
            "number": 1,
            "prompt": "changed",
            "duration_seconds": 99,
            "camera": "wide",
            "lighting": "soft",
            "style": "realistic",
            "character_ids": ["person-OTHER"],
            "location_ids": ["place-1"],
        }
    ])
    with pytest.raises(RuntimeError, match="AI_PROVIDER_CONTINUITY_VIOLATION:shot canonical IDs changed"):
        AIScenePlanner(_registry(payload)).plan_shots(ContentBrief("test"), _story().scenes[0], "test-model")


def test_shot_planner_preserves_ids_and_duration() -> None:
    payload = json.dumps([
        {
            "number": 1,
            "prompt": "precise cinematic shot",
            "duration_seconds": 99,
            "camera": "wide",
            "lighting": "soft",
            "style": "realistic",
            "character_ids": ["person-1"],
            "location_ids": ["place-1"],
        }
    ])
    planner = AIScenePlanner(_registry(payload))
    result = planner.plan_shots(ContentBrief("test"), _story().scenes[0], "test-model")
    assert result[0].prompt == "precise cinematic shot"
    assert result[0].duration_seconds == 10
    assert result[0].character_ids == ("person-1",)
    assert result[0].location_ids == ("place-1",)
