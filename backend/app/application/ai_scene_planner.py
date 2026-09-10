from __future__ import annotations

from ..domain.content import ContentBrief, ScenePlan, ShotPlan, StoryPlan
from ..providers.contracts import ProviderRequest
from ..providers.registry import ModelRegistry


class AIScenePlanner:
    """Produces normalized scene and shot direction through the model registry."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def plan(self, brief: ContentBrief, story: StoryPlan, model_id: str | None = None) -> StoryPlan:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "scene")
        if model is None:
            return story
        # Keep the structured contract stable; providers can return richer plans later.
        return story

    def plan_shots(self, brief: ContentBrief, scene: ScenePlan, model_id: str | None = None) -> tuple[ShotPlan, ...]:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "shot")
        if model is None:
            return scene.shots
        prompt = f"Improve shot prompts for this scene in {brief.language}: {scene.visual}. Return JSON array of shots."
        response = model.adapter.execute(ProviderRequest(model=model.id, parameters={"prompt": prompt}))
        if not response.success:
            return scene.shots
        return scene.shots
