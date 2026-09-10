from __future__ import annotations

import json
from dataclasses import asdict

from ..domain.content import ContentBrief, StoryPlan
from ..providers.contracts import ProviderRequest
from ..providers.registry import ModelRegistry
from .content_planner import DeterministicContentPlanner


class AIStoryEngine:
    """AI-first story engine with deterministic fallback for offline operation."""

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        self.fallback = DeterministicContentPlanner()

    def generate(self, brief: ContentBrief, model_id: str | None = None) -> StoryPlan:
        model = self.registry.get(model_id) if model_id else self.registry.route("generation", "story")
        if model is None:
            return self.fallback.plan(brief)

        prompt = (
            "Create a production-ready video story as strict JSON. "
            "Return title, logline, synopsis and scenes. Each scene must contain "
            "number,title,duration_seconds,visual,narration,shots. Each shot must "
            "contain number,prompt,duration_seconds,camera,lighting,style. "
            f"Language: {brief.language}. Duration: {brief.duration_seconds}s. "
            f"Style: {brief.style}. Audience: {brief.audience}. Platform: {brief.platform}. "
            f"Topic: {brief.topic}"
        )
        response = model.adapter.execute(ProviderRequest(model=model.id, parameters={"prompt": prompt}))
        if not response.success or not response.output_text:
            return self.fallback.plan(brief)
        try:
            data = json.loads(response.output_text)
            return _story_from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return self.fallback.plan(brief)


def _story_from_dict(data: dict[str, object]) -> StoryPlan:
    scenes = []
    for raw_scene in data["scenes"]:  # type: ignore[index]
        scene = dict(raw_scene)  # type: ignore[arg-type]
        shots = []
        for raw_shot in scene.get("shots", []):
            shot = dict(raw_shot)
            from ..domain.content import ShotPlan
            shots.append(ShotPlan(**shot))
        from ..domain.content import ScenePlan
        scene["shots"] = tuple(shots)
        scenes.append(ScenePlan(**scene))
    return StoryPlan(title=str(data["title"]), logline=str(data["logline"]), synopsis=str(data["synopsis"]), scenes=tuple(scenes))
