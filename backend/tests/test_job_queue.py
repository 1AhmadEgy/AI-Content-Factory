from datetime import timedelta

import pytest

from app.domain.jobs import GenerationJob, JobStatus, JobType, utc_now
from app.domain.projects import Project
from app.infrastructure.sqlite import SQLiteRepositories
from app.infrastructure.sqlite_queue import SQLiteJobQueue
from app.orchestrator.queue import JobLease


def _job(job_id: str, *, priority: int = 50, max_attempts: int = 3) -> GenerationJob:
    return GenerationJob(
        id=job_id,
        project_id="project-1",
        type=JobType.IMAGE,
        target_type="shot",
        status=JobStatus.QUEUED,
        priority=priority,
        max_attempts=max_attempts,
    )


def _setup(*jobs: GenerationJob) -> tuple[SQLiteRepositories, SQLiteJobQueue]:
    repositories = SQLiteRepositories(":memory:")
    repositories.projects.create(Project(id="project-1", name="Queue Test"))
    for job in jobs:
        repositories.jobs.create(job)
    return repositories, SQLiteJobQueue(repositories.store, repositories.jobs)


def test_priority_order_and_single_claim() -> None:
    repositories, queue = _setup(_job("low", priority=10), _job("high", priority=100))
    try:
        first = queue.claim_next("worker-a")
        second = queue.claim_next("worker-b")
        assert first is not None and first[0].id == "high"
        assert second is not None and second[0].id == "low"
        assert queue.claim_next("worker-c") is None
    finally:
        repositories.close()


def test_targeted_claim_is_atomic() -> None:
    repositories, queue = _setup(_job("job-1"))
    try:
        first = queue.claim("job-1", "worker-a")
        second = queue.claim("job-1", "worker-b")
        assert first is not None
        assert second is None
        persisted = repositories.jobs.get("job-1")
        assert persisted is not None
        assert persisted.status is JobStatus.RUNNING
        assert persisted.attempt == 1
    finally:
        repositories.close()


def test_wrong_lease_cannot_heartbeat_or_acknowledge() -> None:
    repositories, queue = _setup(_job("job-1"))
    try:
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


def test_expired_lease_recovers_job_and_preserves_retry_budget() -> None:
    repositories, queue = _setup(_job("job-1", max_attempts=3))
    try:
        claimed = queue.claim("job-1", "worker-a")
        assert claimed is not None
        with repositories.store._lock, repositories.store.connection:
            repositories.store.connection.execute(
                "UPDATE job_leases SET expires_at=? WHERE job_id=?",
                ((utc_now() - timedelta(seconds=1)).isoformat(), "job-1"),
            )
        assert queue.release_expired() == 1
        persisted = repositories.jobs.get("job-1")
        assert persisted is not None
        assert persisted.status is JobStatus.RETRYING
        assert persisted.attempt == 1
        assert persisted.error_code == "LEASE_EXPIRED"
    finally:
        repositories.close()


def test_expired_lease_at_retry_limit_fails_closed() -> None:
    repositories, queue = _setup(_job("job-1", max_attempts=1))
    try:
        claimed = queue.claim("job-1", "worker-a")
        assert claimed is not None
        with repositories.store._lock, repositories.store.connection:
            repositories.store.connection.execute(
                "UPDATE job_leases SET expires_at=? WHERE job_id=?",
                ((utc_now() - timedelta(seconds=1)).isoformat(), "job-1"),
            )
        assert queue.release_expired() == 1
        persisted = repositories.jobs.get("job-1")
        assert persisted is not None
        assert persisted.status is JobStatus.FAILED
        assert persisted.error_code == "LEASE_EXPIRED"
    finally:
        repositories.close()
