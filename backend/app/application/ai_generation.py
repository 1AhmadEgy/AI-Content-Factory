from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..domain.content import ContentBrief, ScenePlan, ShotPlan
from ..domain.jobs import GenerationJob, JobInput, JobType


@dataclass(frozen=True, slots=True)
class GenerationSpec:
    job_type: JobType
    prompt: str
    negative_prompt: str = ""
    duration_seconds: float | None = None
    parameters: dict[str, Any] | None = None


class AIGenerationPlanner:
    """Create generation specifications only for provider capabilities implemented in production."""

    def image(self, brief: ContentBrief, scene: ScenePlan, shot: ShotPlan, take: int = 1) -> GenerationSpec:
        return GenerationSpec(JobType.IMAGE, self._visual_prompt(brief, scene, shot), "blurry, distorted, duplicate subjects, text, watermark", parameters={"aspect_ratio": brief.aspect_ratio, "take": take, "scene": scene.number, "shot": shot.number})

    def tts(self, brief: ContentBrief, scene: ScenePlan) -> GenerationSpec:
        return GenerationSpec(JobType.TTS, scene.narration, parameters={"language": brief.language, "scene": scene.number})

    @staticmethod
    def _visual_prompt(brief: ContentBrief, scene: ScenePlan, shot: ShotPlan) -> str:
        return f"{shot.prompt}. Scene: {scene.visual}. Camera: {shot.camera}. Lighting: {shot.lighting}. Style: {shot.style}. Audience: {brief.audience}. Platform: {brief.platform}."

    def to_job(self, project_id: str, target_id: str, parent_job_id: str | None, spec: GenerationSpec, model: str | None = None) -> GenerationJob:
        return GenerationJob(id="", project_id=project_id, type=spec.job_type, target_type=spec.job_type.value, target_id=target_id, parent_job_id=parent_job_id, model=model, input=JobInput(parameters={"prompt": spec.prompt, "negative_prompt": spec.negative_prompt, **(spec.parameters or {})}))
