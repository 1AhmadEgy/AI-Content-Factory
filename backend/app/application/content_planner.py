from __future__ import annotations

from ..domain.content import ContentBrief, ScenePlan, ShotPlan, StoryPlan


class DeterministicContentPlanner:
    """Offline planner used for development, tests, and zero-cost mock mode.

    It deliberately produces structured production data rather than pretending to
    be an external LLM. Cloud/local model adapters can replace this implementation
    without changing the API contract.
    """

    def plan(self, brief: ContentBrief) -> StoryPlan:
        duration = max(15, brief.duration_seconds)
        scene_count = 3 if duration < 120 else 5
        base = duration // scene_count
        remainder = duration % scene_count
        scenes: list[ScenePlan] = []

        for index in range(scene_count):
            scene_duration = base + (1 if index < remainder else 0)
            scene_number = index + 1
            visual = f"{brief.style} visual sequence about: {brief.topic}"
            narration = f"{brief.topic} — section {scene_number}."
            shot_count = 2 if scene_duration >= 10 else 1
            shot_duration = max(1, scene_duration // shot_count)
            shots = tuple(
                ShotPlan(
                    number=shot_index + 1,
                    prompt=f"{visual}; shot {shot_index + 1}",
                    duration_seconds=shot_duration,
                    camera="wide" if shot_index == 0 else "medium",
                    lighting="cinematic",
                    style=brief.style,
                )
                for shot_index in range(shot_count)
            )
            scenes.append(
                ScenePlan(
                    number=scene_number,
                    title=f"Scene {scene_number}",
                    duration_seconds=scene_duration,
                    visual=visual,
                    narration=narration,
                    shots=shots,
                )
            )

        return StoryPlan(
            title=brief.topic[:120],
            logline=f"A {brief.style} production about {brief.topic}.",
            synopsis=f"A structured {brief.duration_seconds}-second {brief.platform} production for {brief.audience} viewers.",
            scenes=tuple(scenes),
        )
