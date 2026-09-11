from datetime import timedelta

import pytest

from backend.app.domain.jobs import GenerationJob, JobStatus, JobType, utc_now
from backend.app.domain.projects import Project
from backend.app.infrastructure.sqlite import SQLiteRepositories
from backend.app.infrastructure.sqlite_queue import SQLiteJobQueue
from backend.app.orchestrator.queue import JobLease


def _job(job_id: str, *, max_attempts: int = 3) -> GenerationJob:
    return GenerationJob(
        id=job_id,
        project_id="project-1",
        type=JobType.IMAGE,
        target_type="shot",
        status=JobStatus.QUEUED,
        max_attempts=max_attempts,
    )


def test_targeted_claim_is_single_owner() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        repositories.jobs.create(_job("job-1"))
        queue = SQLiteJobQueue(repositories.store, repositories.jobs)

        first = queue.claim("job-1", "worker-a")
        second = queue.claim("job-1", "worker-b")

        assert first is not None
        assert first[1].worker_id == "worker-a"
        assert second is None
        persisted = repositories.jobs.get("job-1")
        assert persisted is not None
        assert persisted.status is JobStatus.RUNNING
        assert persisted.attempt == 1
    finally:
        repositories.close()


def test_wrong_lease_cannot_heartbeat_or_acknowledge() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        repositories.jobs.create(_job("job-1"))
        queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        claimed = queue.claim("job-1", "worker-a")
        assert claimed is not None
        _, lease = claimed

        forged = JobLease(
            job_id=lease.job_id,
            worker_id="worker-b",
            lease_id="forged-lease",
            expires_at=lease.expires_at,
        )
        with pytest.raises(KeyError, match="JOB_LEASE_NOT_FOUND"):
            queue.heartbeat(forged)
        with pytest.raises(KeyError, match="JOB_LEASE_NOT_FOUND"):
            queue.acknowledge(forged, JobStatus.COMPLETED)

        assert queue.is_lease_active(lease)
    finally:
        repositories.close()


def test_expired_lease_exhausts_retry_budget_and_fails() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        repositories.jobs.create(_job("job-1", max_attempts=1))
        queue = SQLiteJobQueue(repositories.store, repositories.jobs, lease_seconds=300)
        claimed = queue.claim("job-1", "worker-a")
        assert claimed is not None

        expired = utc_now() - timedelta(seconds=1)
        with repositories.store._lock, repositories.store.connection:
            repositories.store.connection.execute(
                "UPDATE job_leases SET expires_at=? WHERE job_id=?",
                (expired.isoformat(), "job-1"),
            )

        assert queue.release_expired() == 1
        persisted = repositories.jobs.get("job-1")
        assert persisted is not None
        assert persisted.status is JobStatus.FAILED
        assert persisted.error_code == "LEASE_EXPIRED"
    finally:
        repositories.close()
