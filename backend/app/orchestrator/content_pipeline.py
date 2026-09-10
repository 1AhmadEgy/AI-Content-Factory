from __future__ import annotations

from ..domain.jobs import GenerationJob, JobInput, JobType
from .job_service import JobService


class ContentPipelineOrchestrator:
    """Expand a completed STORY into durable SCENE and SHOT jobs."""

    def __init__(self, job_service: JobService, enqueue) -> None:
        self.job_service = job_service
        self.enqueue = enqueue

    def on_completed(self, job: GenerationJob) -> list[GenerationJob]:
        if job.type is not JobType.STORY:
            return []
        plan = job.input.parameters.get("plan")
        if not isinstance(plan, dict):
            return []
        scenes = plan.get("scenes", [])
        if not isinstance(scenes, list):
            return []

        created: list[GenerationJob] = []
        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            scene_number = int(scene.get("number", len(created) + 1))
            scene_id = f"{job.id}:scene:{scene_number}"
            scene_job = self.job_service.create(
                project_id=job.project_id, job_type=JobType.SCENE,
                target_type="scene", target_id=scene_id,
                parent_job_id=job.id, priority=max(job.priority - 1, 0),
                provider=job.provider, model=job.model,
                input=JobInput(
                    parameters={"scene": scene, "storyJobId": job.id, "sceneNumber": scene_number},
                    deterministic=job.input.deterministic,
                ),
            )
            self.enqueue(scene_job)
            created.append(scene_job)

            shots = scene.get("shots", [])
            if not isinstance(shots, list):
                continue
            for shot in shots:
                if not isinstance(shot, dict):
                    continue
                shot_number = int(shot.get("number", 1))
                shot_id = f"{scene_id}:shot:{shot_number}"
                shot_job = self.job_service.create(
                    project_id=job.project_id, job_type=JobType.SHOT,
                    target_type="shot", target_id=shot_id,
                    parent_job_id=scene_job.id, priority=max(job.priority - 2, 0),
                    provider=job.provider, model=job.model,
                    input=JobInput(
                        parameters={"shot": shot, "sceneJobId": scene_job.id,
                                    "sceneNumber": scene_number, "shotNumber": shot_number},
                        deterministic=job.input.deterministic,
                    ),
                )
                self.enqueue(shot_job)
                created.append(shot_job)
        return created
