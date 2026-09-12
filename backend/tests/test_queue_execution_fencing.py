from datetime import timedelta

from app.domain.jobs import GenerationJob, JobStatus, JobType, utc_now
from app.domain.projects import Project
from app.infrastructure.sqlite import SQLiteRepositories
from app.infrastructure.sqlite_queue import SQLiteJobQueue


def _job(job_id: str) -> GenerationJob:
    return GenerationJob(
        id=job_id,
        project_id="project-1",
        type=JobType.IMAGE,
        target_type="shot",
        status=JobStatus.QUEUED,
        max_attempts=3,
    )


def test_expired_worker_cannot_overwrite_reclaimed_attempt() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        original = _job("job-1")
        repositories.jobs.create(original)
        queue = SQLiteJobQueue(repositories.store, repositories.jobs, lease_seconds=300)

        claimed_a = queue.claim_next("worker-a")
        assert claimed_a is not None
        stale_job, stale_lease = claimed_a
        assert stale_job.attempt == 1

        expired = utc_now() - timedelta(seconds=1)
        with repositories.store._lock, repositories.store.connection:
            repositories.store.connection.execute(
                "UPDATE job_leases SET expires_at=? WHERE job_id=?",
                (expired.isoformat(), "job-1"),
            )

        assert queue.release_expired() == 1

        claimed_b = queue.claim_next("worker-b")
        assert claimed_b is not None
        current_job, current_lease = claimed_b
        assert current_job.attempt == 2
        assert current_lease.worker_id == "worker-b"

        stale_job.output = None
        stale_job.error_code = "STALE_WORKER_RESULT"
        stale_job.error_message = "Must never overwrite attempt 2"
        stale_job.status = JobStatus.FAILED
        assert repositories.jobs.update_if_current(
            stale_job,
            JobStatus.RUNNING,
            stale_job.attempt,
        ) is False

        persisted = repositories.jobs.get("job-1")
        assert persisted is not None
        assert persisted.status is JobStatus.RUNNING
        assert persisted.attempt == 2
        assert persisted.error_code == "LEASE_EXPIRED"
        assert queue.is_lease_active(current_lease)
        assert not queue.is_lease_active(stale_lease)
    finally:
        repositories.close()
