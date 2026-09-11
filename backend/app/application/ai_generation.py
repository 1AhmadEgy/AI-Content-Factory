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
    """Converts AI-directed shots into provider-neutral generation specifications."""

    def image(self, brief: ContentBrief, scene: ScenePlan, shot: ShotPlan, take: int = 1) -> GenerationSpec:
        return GenerationSpec(JobType.IMAGE, self._visual_prompt(brief, scene, shot), "blurry, distorted, duplicate subjects, text, watermark", parameters={"aspect_ratio": brief.aspect_ratio, "take": take, "scene": scene.number, "shot": shot.number})

    def video(self, brief: ContentBrief, scene: ScenePlan, shot: ShotPlan, take: int = 1) -> GenerationSpec:
        return GenerationSpec(JobType.VIDEO, self._visual_prompt(brief, scene, shot) + f" Motion duration {shot.duration_seconds:.2f}s.", "flicker, jitter, warped anatomy, frame artifacts, text, watermark", shot.duration_seconds, {"aspect_ratio": brief.aspect_ratio, "take": take, "scene": scene.number, "shot": shot.number})

    def tts(self, brief: ContentBrief, scene: ScenePlan) -> GenerationSpec:
        return GenerationSpec(JobType.TTS, scene.narration, parameters={"language": brief.language, "scene": scene.number})

    def audio(self, brief: ContentBrief, scene: ScenePlan, kind: JobType | str) -> GenerationSpec:
        if isinstance(kind, str):
            normalized = kind.strip().upper()
            try:
                kind = JobType(normalized)
            except ValueError as exc:
                raise ValueError(f"Unsupported audio kind: {kind}") from exc
        if kind not in {JobType.MUSIC, JobType.SFX}:
            raise ValueError(f"Unsupported audio kind: {kind}")
        text = f"Create {kind.value.lower()} for scene {scene.number}: {scene.visual}. Style: {brief.style}."
        return GenerationSpec(kind, text, parameters={"language": brief.language, "duration_seconds": scene.duration_seconds, "scene": scene.number})

    @staticmethod
    def _visual_prompt(brief: ContentBrief, scene: ScenePlan, shot: ShotPlan) -> str:
        return f"{shot.prompt}. Scene: {scene.visual}. Camera: {shot.camera}. Lighting: {shot.lighting}. Style: {shot.style}. Audience: {brief.audience}. Platform: {brief.platform}."

    def to_job(self, project_id: str, target_id: str, parent_job_id: str | None, spec: GenerationSpec, model: str | None = None) -> GenerationJob:
        return GenerationJob(id="", project_id=project_id, type=spec.job_type, target_type=spec.job_type.value, target_id=target_id, parent_job_id=parent_job_id, model=model, input=JobInput(parameters={"prompt": spec.prompt, "negative_prompt": spec.negative_prompt, **(spec.parameters or {})}))
