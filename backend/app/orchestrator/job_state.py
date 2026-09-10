from datetime import datetime

from ..domain.jobs import GenerationJob, JobStatus, utc_now


class InvalidJobTransition(ValueError):
    """Raised when a job lifecycle transition violates the contract."""


_ALLOWED: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PENDING: {JobStatus.QUEUED, JobStatus.CANCELLED},
    JobStatus.QUEUED: {JobStatus.RUNNING, JobStatus.PAUSED, JobStatus.CANCELLED},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.RETRYING, JobStatus.PAUSED, JobStatus.CANCELLED, JobStatus.BLOCKED},
    JobStatus.PAUSED: {JobStatus.QUEUED, JobStatus.CANCELLED},
    JobStatus.RETRYING: {JobStatus.QUEUED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.BLOCKED: {JobStatus.QUEUED, JobStatus.CANCELLED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
}


def transition(job: GenerationJob, target: JobStatus, *, now: datetime | None = None) -> GenerationJob:
    if target not in _ALLOWED[job.status]:
        raise InvalidJobTransition(f"Cannot transition {job.status} -> {target}")

    now = now or utc_now()
    job.status = target
    job.updated_at = now

    if target == JobStatus.RUNNING:
        job.attempt += 1
        job.started_at = now
        job.progress = max(job.progress, 0.0)
    elif target == JobStatus.COMPLETED:
        job.progress = 1.0
        job.completed_at = now
    elif target in {JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.BLOCKED}:
        job.completed_at = now

    return job
