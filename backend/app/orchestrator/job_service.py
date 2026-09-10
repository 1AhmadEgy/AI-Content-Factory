from uuid import uuid4

from ..domain.jobs import GenerationJob, JobInput, JobStatus, JobType, utc_now
from ..domain.repositories import IdempotencyResult, JobRepository
from .job_state import transition


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    def create(
        self,
        *,
        project_id: str,
        job_type: JobType,
        target_type: str,
        target_id: str | None = None,
        parent_job_id: str | None = None,
        input: JobInput | None = None,
        priority: int = 100,
        max_attempts: int = 3,
        provider: str | None = None,
        model: str | None = None,
    ) -> GenerationJob:
        return self.repository.create(
            self._new_job(
                project_id=project_id,
                job_type=job_type,
                target_type=target_type,
                target_id=target_id,
                parent_job_id=parent_job_id,
                input=input,
                priority=priority,
                max_attempts=max_attempts,
                provider=provider,
                model=model,
            )
        )

    def create_with_idempotency(
        self,
        *,
        key: str,
        operation: str,
        fingerprint: str,
        project_id: str,
        job_type: JobType,
        target_type: str,
        target_id: str | None = None,
        parent_job_id: str | None = None,
        input: JobInput | None = None,
        priority: int = 100,
        max_attempts: int = 3,
        provider: str | None = None,
        model: str | None = None,
    ) -> IdempotencyResult:
        """Create a job through the repository's atomic idempotency boundary."""
        job = self._new_job(
            project_id=project_id,
            job_type=job_type,
            target_type=target_type,
            target_id=target_id,
            parent_job_id=parent_job_id,
            input=input,
            priority=priority,
            max_attempts=max_attempts,
            provider=provider,
            model=model,
        )
        result = self.repository.create_with_idempotency(
            job,
            key=key,
            operation=operation,
            fingerprint=fingerprint,
        )
        if result is None:
            raise RuntimeError("IDEMPOTENCY_NOT_SUPPORTED")
        return result

    def cancel(self, job_id: str) -> GenerationJob:
        job = self._get(job_id)
        if job.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            return job
        expected_status = job.status
        transition(job, JobStatus.CANCELLED)
        job.error_code = "CANCELLED_BY_USER"
        job.error_message = "Job cancelled by user"
        return self._update_if_current(job, expected_status)

    def pause(self, job_id: str) -> GenerationJob:
        job = self._get(job_id)
        if job.status is not JobStatus.QUEUED:
            raise ValueError("JOB_NOT_PAUSABLE")
        expected_status = job.status
        transition(job, JobStatus.PAUSED)
        return self._update_if_current(job, expected_status)

    def resume(self, job_id: str) -> GenerationJob:
        job = self._get(job_id)
        if job.status not in {JobStatus.PAUSED, JobStatus.RETRYING, JobStatus.BLOCKED}:
            raise ValueError("JOB_NOT_RESUMABLE")
        expected_status = job.status
        transition(job, JobStatus.QUEUED)
        job.error_code = None
        job.error_message = None
        job.completed_at = None
        job.updated_at = utc_now()
        return self._update_if_current(job, expected_status)

    def retry(self, job_id: str) -> GenerationJob:
        job = self._get(job_id)
        if job.status not in {JobStatus.FAILED, JobStatus.RETRYING}:
            raise ValueError("JOB_NOT_RETRYABLE")
        if job.attempt >= job.max_attempts:
            raise ValueError("MAX_ATTEMPTS_REACHED")
        expected_status = job.status
        if job.status is JobStatus.FAILED:
            transition(job, JobStatus.RETRYING)
        transition(job, JobStatus.QUEUED)
        job.error_code = None
        job.error_message = None
        job.completed_at = None
        job.updated_at = utc_now()
        return self._update_if_current(job, expected_status)

    def _update_if_current(self, job: GenerationJob, expected_status: JobStatus) -> GenerationJob:
        if not self.repository.update_if_current(job, expected_status, job.attempt):
            raise RuntimeError("JOB_STATE_CONFLICT")
        return job

    def _new_job(
        self,
        *,
        project_id: str,
        job_type: JobType,
        target_type: str,
        target_id: str | None,
        parent_job_id: str | None,
        input: JobInput | None,
        priority: int,
        max_attempts: int,
        provider: str | None,
        model: str | None,
    ) -> GenerationJob:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        job = GenerationJob(
            id=str(uuid4()),
            project_id=project_id,
            type=job_type,
            target_type=target_type,
            target_id=target_id,
            parent_job_id=parent_job_id,
            input=input or JobInput(),
            priority=priority,
            max_attempts=max_attempts,
            provider=provider,
            model=model,
        )
        return transition(job, JobStatus.QUEUED)

    def _get(self, job_id: str) -> GenerationJob:
        job = self.repository.get(job_id)
        if job is None:
            raise KeyError("JOB_NOT_FOUND")
        return job
