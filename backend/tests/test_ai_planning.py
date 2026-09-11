from __future__ import annotations

import pytest

from app.application.ai_scene_planner import AIScenePlanner
from app.application.ai_story_engine import AIStoryEngine
from app.domain.content import ContentBrief, ScenePlan, ShotPlan, StoryPlan
from app.providers.registry import ModelRegistry


def _story() -> StoryPlan:
    return StoryPlan(
        "Title", "Logline", "Synopsis",
        (ScenePlan(1, "Scene", 10, "Visual", "Narration", (ShotPlan(1, "prompt", 10),)),),
    )


def test_story_engine_requires_configured_provider() -> None:
    with pytest.raises(RuntimeError, match="AI_PROVIDER_NOT_CONFIGURED:story"):
        AIStoryEngine(ModelRegistry()).generate(ContentBrief("space"))


def test_scene_planner_requires_configured_provider() -> None:
    planner = AIScenePlanner(ModelRegistry())
    with pytest.raises(RuntimeError, match="AI_PROVIDER_NOT_CONFIGURED:scene"):
        planner.plan(ContentBrief("test"), _story())


def test_shot_planner_requires_configured_provider() -> None:
    planner = AIScenePlanner(ModelRegistry())
    with pytest.raises(RuntimeError, match="AI_PROVIDER_NOT_CONFIGURED:shot"):
        planner.plan_shots(ContentBrief("test"), _story().scenes[0])
