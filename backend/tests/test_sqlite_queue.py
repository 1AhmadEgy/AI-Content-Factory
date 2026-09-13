from datetime import timedelta

import pytest

from app.domain.jobs import GenerationJob, JobStatus, JobType, utc_now
from app.domain.projects import Project
from app.infrastructure.sqlite import SQLiteRepositories
from app.infrastructure.sqlite_queue import SQLiteJobQueue


def _queued_job(job_id: str, priority: int) -> GenerationJob:
    return GenerationJob(id=job_id, project_id="project-1", type=JobType.IMAGE, target_type="shot", status=JobStatus.QUEUED, priority=priority)


def test_claim_orders_by_priority_and_prevents_double_claim() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        repositories.jobs.create(_queued_job("low", 10))
        repositories.jobs.create(_queued_job("high", 100))
        queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        first = queue.claim_next("worker-a")
        second = queue.claim_next("worker-b")
        assert first is not None and first[0].id == "high"
        assert second is not None and second[0].id == "low"
        assert queue.claim_next("worker-c") is None
    finally:
        repositories.close()


def test_expired_lease_requeues_job_as_queued() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        repositories.jobs.create(_queued_job("job-1", 50))
        queue = SQLiteJobQueue(repositories.store, repositories.jobs, lease_seconds=300)
        assert queue.claim_next("worker-a") is not None
        expired = utc_now() - timedelta(seconds=1)
        with repositories.store._lock, repositories.store.connection:
            repositories.store.connection.execute("UPDATE job_leases SET expires_at=? WHERE job_id=?", (expired.isoformat(), "job-1"))
        assert queue.release_expired() == 1
        restored = repositories.jobs.get("job-1")
        assert restored is not None and restored.status is JobStatus.QUEUED
        assert restored.error_code == "LEASE_EXPIRED"
        assert queue.claim_next("worker-b") is not None
    finally:
        repositories.close()


def test_heartbeat_and_acknowledge_require_the_lease_owner() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        repositories.jobs.create(_queued_job("job-1", 50))
        queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        claimed = queue.claim_next("worker-a")
        assert claimed is not None
        job, lease = claimed
        foreign = type(lease)(job.id, "worker-b", lease.lease_id, lease.expires_at)
        with pytest.raises(KeyError, match="JOB_LEASE_NOT_FOUND"):
            queue.heartbeat(foreign)
        assert queue.is_lease_active(lease)
        with pytest.raises(KeyError, match="JOB_LEASE_NOT_FOUND"):
            queue.acknowledge(foreign, JobStatus.COMPLETED)
        queue.acknowledge(lease, JobStatus.COMPLETED)
        completed = repositories.jobs.get(job.id)
        assert completed is not None and completed.status is JobStatus.COMPLETED
        assert not queue.is_lease_active(lease)
    finally:
        repositories.close()
