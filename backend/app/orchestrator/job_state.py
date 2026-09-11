from datetime import datetime

from ..domain.jobs import GenerationJob, JobStatus, utc_now


class InvalidJobTransition(ValueError):
    """Raised when a job lifecycle transition violates the contract."""


_ALLOWED: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PENDING: {JobStatus.QUEUED, JobStatus.CANCELLED},
    JobStatus.QUEUED: {JobStatus.LEASED, JobStatus.CANCELLED},
    JobStatus.LEASED: {JobStatus.RUNNING, JobStatus.QUEUED, JobStatus.CANCELLED},
    JobStatus.RUNNING: {JobStatus.QC_PENDING, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.QC_PENDING: {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.SUCCEEDED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
}

_TERMINAL_STATES = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}


def transition(
    job: GenerationJob,
    target: JobStatus,
    *,
    now: datetime | None = None,
) -> GenerationJob:
    if target not in _ALLOWED[job.status]:
        raise InvalidJobTransition(f"Cannot transition {job.status} -> {target}")

    now = now or utc_now()
    job.status = target
    job.updated_at = now

    if target == JobStatus.LEASED:
        job.lease_owner = job.lease_owner
    elif target == JobStatus.RUNNING:
        job.attempt += 1
        job.started_at = now
        job.progress = max(job.progress, 0.0)
    elif target == JobStatus.SUCCEEDED:
        job.progress = 1.0
        job.completed_at = now
    elif target in _TERMINAL_STATES:
        job.completed_at = now

    return job
