from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from app.domain.jobs import GenerationJob, JobStatus, JobType
from app.domain.projects import Project
from app.infrastructure.sqlite import SQLiteJobRepository, SQLiteProjectRepository, SQLiteStore
from app.infrastructure.sqlite_queue import SQLiteJobQueue


def make_queue(lease_seconds: int = 30):
    store = SQLiteStore(":memory:")
    projects = SQLiteProjectRepository(store)
    jobs = SQLiteJobRepository(store)
    projects.create(Project(id="project-1", name="Concurrency test"))
    queue = SQLiteJobQueue(store, jobs, lease_seconds=lease_seconds)
    return store, jobs, queue


def make_queued_job(job_id: str = "job-1", max_attempts: int = 3):
    return GenerationJob(
        id=job_id,
        project_id="project-1",
        type=JobType.IMAGE,
        target_type="shot",
        status=JobStatus.QUEUED,
        max_attempts=max_attempts,
    )


def test_concurrent_claim_allows_exactly_one_worker():
    store, jobs, queue = make_queue()
    try:
        jobs.create(make_queued_job())

        def claim(worker_id):
            return queue.claim("job-1", worker_id)

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(claim, [f"worker-{i}" for i in range(8)]))

        claimed = [result for result in results if result is not None]
        assert len(claimed) == 1
        job, lease = claimed[0]
        assert job.status is JobStatus.RUNNING
        assert job.attempt == 1
        assert lease.job_id == "job-1"
        assert queue.claim("job-1", "late-worker") is None
    finally:
        store.close()


def test_expired_lease_can_be_recovered_and_reclaimed_once():
    store, jobs, queue = make_queue(lease_seconds=30)
    try:
        jobs.create(make_queued_job(max_attempts=3))
        first = queue.claim("job-1", "worker-1")
        assert first is not None
        _, first_lease = first

        expired = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
        with store._lock, store.connection:
            store.connection.execute(
                "UPDATE job_leases SET expires_at=? WHERE job_id=? AND lease_id=?",
                (expired, first_lease.job_id, first_lease.lease_id),
            )

        assert queue.release_expired() == 1
        recovered = jobs.get("job-1")
        assert recovered is not None
        assert recovered.status is JobStatus.RETRYING

        second = queue.claim("job-1", "worker-2")
        assert second is not None
        second_job, second_lease = second
        assert second_job.status is JobStatus.RUNNING
        assert second_job.attempt == 2
        assert second_lease.lease_id != first_lease.lease_id
        assert queue.claim("job-1", "worker-3") is None
    finally:
        store.close()


def test_expired_worker_cannot_acknowledge_after_recovery():
    store, jobs, queue = make_queue(lease_seconds=30)
    try:
        jobs.create(make_queued_job(max_attempts=3))
        first = queue.claim("job-1", "worker-1")
        assert first is not None
        first_job, first_lease = first

        expired = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
        with store._lock, store.connection:
            store.connection.execute(
                "UPDATE job_leases SET expires_at=? WHERE job_id=? AND lease_id=?",
                (expired, first_lease.job_id, first_lease.lease_id),
            )

        assert queue.release_expired() == 1
        second = queue.claim("job-1", "worker-2")
        assert second is not None

        with pytest.raises(KeyError, match="JOB_LEASE_NOT_FOUND"):
            queue.acknowledge(first_lease, JobStatus.COMPLETED)

        current = jobs.get(first_job.id)
        assert current is not None
        assert current.status is JobStatus.RUNNING
        assert current.attempt == 2
    finally:
        store.close()
