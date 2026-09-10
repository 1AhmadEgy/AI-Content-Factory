from __future__ import annotations

from ..domain.jobs import GenerationJob, JobInput, JobType
from .job_service import JobService


class ContentPipelineOrchestrator:
    """Expand completed planning jobs into the next durable production stage."""

    def __init__(self, job_service: JobService, enqueue) -> None:
        self.job_service = job_service
        self.enqueue = enqueue

    def on_completed(self, job: GenerationJob) -> list[GenerationJob]:
        if job.type is JobType.STORY:
            return self._create_scene_jobs(job)
        if job.type is JobType.SCENE:
            return self._create_shot_jobs(job)
        if job.type is JobType.SHOT:
            return self._create_generation_jobs(job)
        return []

    def _create_scene_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        plan = job.input.parameters.get("plan")
        if not isinstance(plan, dict):
            return []
        scenes = plan.get("scenes", [])
        if not isinstance(scenes, list):
            return []
        created: list[GenerationJob] = []
        for index, scene in enumerate(scenes, 1):
            if not isinstance(scene, dict):
                continue
            number = int(scene.get("number", index))
            scene_id = f"{job.id}:scene:{number}"
            created.append(self._enqueue(
                job,
                JobType.SCENE,
                "scene",
                scene_id,
                {"scene": scene, "storyJobId": job.id, "sceneNumber": number},
                1,
            ))
        return created

    def _create_shot_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        scene = job.input.parameters.get("scene")
        if not isinstance(scene, dict):
            return []
        shots = scene.get("shots", [])
        if not isinstance(shots, list):
            return []
        scene_id = job.target_id or f"{job.id}:scene"
        created: list[GenerationJob] = []
        for index, shot in enumerate(shots, 1):
            if not isinstance(shot, dict):
                continue
            number = int(shot.get("number", index))
            shot_id = f"{scene_id}:shot:{number}"
            created.append(self._enqueue(
                job,
                JobType.SHOT,
                "shot",
                shot_id,
                {"shot": shot, "sceneJobId": job.id, "sceneNumber": job.input.parameters.get("sceneNumber"), "shotNumber": number},
                2,
            ))
        return created

    def _create_generation_jobs(self, job: GenerationJob) -> list[GenerationJob]:
        shot = job.input.parameters.get("shot")
        if not isinstance(shot, dict):
            return []
        common = {"shot": shot, "shotJobId": job.id, "shotNumber": job.input.parameters.get("shotNumber")}
        created: list[GenerationJob] = []
        for job_type, target in ((JobType.IMAGE, "image"), (JobType.VIDEO, "video"), (JobType.TTS, "voice")):
            created.append(self._enqueue(job, job_type, target, f"{job.id}:{target}", common, 3))
        return created

    def _enqueue(
        self,
        parent: GenerationJob,
        job_type: JobType,
        target_type: str,
        target_id: str,
        parameters: dict[str, object],
        priority_offset: int,
    ) -> GenerationJob:
        child = self.job_service.create(
            project_id=parent.project_id,
            job_type=job_type,
            target_type=target_type,
            target_id=target_id,
            parent_job_id=parent.id,
            priority=max(parent.priority - priority_offset, 0),
            provider=parent.provider,
            model=parent.model,
            input=JobInput(parameters=parameters, deterministic=parent.input.deterministic),
        )
        self.enqueue(child)
        return child
