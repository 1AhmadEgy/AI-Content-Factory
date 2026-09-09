from uuid import uuid4
from ..domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from ..domain.repositories import JobRepository
from .job_state import transition


class JobService:
    def __init__(self, repository: JobRepository):
        self.repository = repository

    def create(
        self,
        *,
        project_id: str,
        job_type: JobType,
        target_type: str,
        target_id: str | None = None,
        input: JobInput | None = None,
        priority: int = 100,
        max_attempts: int = 3,
    ) -> GenerationJob:
        job = GenerationJob(
            id=str(uuid4()),
            project_id=project_id,
            type=job_type,
            target_type=target_type,
            target_id=target_id,
            input=input or JobInput(),
            priority=priority,
            max_attempts=max_attempts,
        )
        transition(job, JobStatus.QUEUED)
        return self.repository.create(job)
