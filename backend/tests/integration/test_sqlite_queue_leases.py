from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier

import pytest

from app.domain.jobs import GenerationJob, JobStatus, JobType, utc_now
from app.domain.projects import Project
from app.infrastructure.sqlite import SQLiteRepositories
from app.infrastructure.sqlite_queue import SQLiteJobQueue


def _queued_job(job_id: str = "job-1", max_attempts: int = 3) -> GenerationJob:
    return GenerationJob(
        id=job_id,
        project_id="project-1",
        type=JobType.IMAGE,
        target_type="shot",
        status=JobStatus.QUEUED,
        max_attempts=max_attempts,
    )


def _repositories(path: str | Path = ":memory:") -> SQLiteRepositories:
    repositories = SQLiteRepositories(path)
    repositories.projects.create(Project(id="project-1", name="Lease Test"))
    repositories.jobs.create(_queued_job())
    return repositories


def _set_lease_expiry(repositories: SQLiteRepositories, delta: timedelta, job_id: str = "job-1") -> None:
    expires_at = utc_now() + delta
    with repositories.store._lock, repositories.store.connection:
        repositories.store.connection.execute(
            "UPDATE job_leases SET expires_at=? WHERE job_id=?",
            (expires_at.isoformat(), job_id),
        )


def test_claim_is_exclusive_under_real_sqlite_concurrency() -> None:
    with TemporaryDirectory() as directory:
        db_path = Path(directory) / "queue.db"
        repositories_a = _repositories(db_path)
        repositories_b = SQLiteRepositories(db_path)
        try:
            queue_a = SQLiteJobQueue(repositories_a.store, repositories_a.jobs)
            queue_b = SQLiteJobQueue(repositories_b.store, repositories_b.jobs)
            barrier = Barrier(2)

            def claim(queue: SQLiteJobQueue, worker_id: str):
                barrier.wait(timeout=5)
                return queue.claim("job-1", worker_id)

            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(claim, queue_a, "worker-a")
                second = executor.submit(claim, queue_b, "worker-b")
                results = [first.result(timeout=10), second.result(timeout=10)]

            winners = [result for result in results if result is not None]
            assert len(winners) == 1
            assert winners[0][1].worker_id in {"worker-a", "worker-b"}
        finally:
            repositories_b.close()
            repositories_a.close()


def test_expired_lease_can_be_reclaimed_with_new_lease_and_attempt() -> None:
    repositories = _repositories()
    try:
        queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        claimed_a = queue.claim("job-1", "worker-a")
        assert claimed_a is not None
        job_a, lease_a = claimed_a

        _set_lease_expiry(repositories, timedelta(seconds=-1))
        assert queue.release_expired() == 1

        claimed_b = queue.claim("job-1", "worker-b")
        assert claimed_b is not None
        job_b, lease_b = claimed_b

        assert lease_b.lease_id != lease_a.lease_id
        assert job_b.attempt > job_a.attempt
        assert lease_b.worker_id == "worker-b"
    finally:
        repositories.close()


def test_stale_worker_cannot_update_after_reclaim() -> None:
    repositories = _repositories()
    try:
        queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        claimed_a = queue.claim("job-1", "worker-a")
        assert claimed_a is not None
        job_a, lease_a = claimed_a

        _set_lease_expiry(repositories, timedelta(seconds=-1))
        assert queue.release_expired() == 1

        claimed_b = queue.claim("job-1", "worker-b")
        assert claimed_b is not None
        job_b, lease_b = claimed_b

        job_a.error_code = "STALE_WORKER"
        assert repositories.jobs.update_if_current(
            job_a,
            JobStatus.RUNNING,
            job_a.attempt,
        ) is False

        job_b.error_code = "CURRENT_WORKER"
        assert repositories.jobs.update_if_current(
            job_b,
            JobStatus.RUNNING,
            job_b.attempt,
        ) is True

        current = repositories.jobs.get("job-1")
        assert current is not None
        assert current.error_code == "CURRENT_WORKER"

        with pytest.raises(KeyError, match="JOB_LEASE_NOT_FOUND"):
            queue.acknowledge(lease_a, JobStatus.COMPLETED)

        assert lease_b.lease_id != lease_a.lease_id
    finally:
        repositories.close()


def test_stale_worker_cannot_heartbeat_after_reclaim() -> None:
    repositories = _repositories()
    try:
        queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        claimed_a = queue.claim("job-1", "worker-a")
        assert claimed_a is not None
        _, lease_a = claimed_a

        _set_lease_expiry(repositories, timedelta(seconds=-1))
        assert queue.release_expired() == 1
        assert queue.claim("job-1", "worker-b") is not None

        with pytest.raises(KeyError, match="JOB_LEASE_NOT_FOUND"):
            queue.heartbeat(lease_a)
    finally:
        repositories.close()


def test_current_worker_can_update() -> None:
    repositories = _repositories()
    try:
        queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        claimed = queue.claim("job-1", "worker-a")
        assert claimed is not None
        job, lease = claimed

        job.error_code = "CURRENT"
        assert repositories.jobs.update_if_current(
            job,
            JobStatus.RUNNING,
            job.attempt,
        ) is True

        current = repositories.jobs.get("job-1")
        assert current is not None
        assert current.error_code == "CURRENT"

        queue.acknowledge(lease, JobStatus.COMPLETED)
        completed = repositories.jobs.get("job-1")
        assert completed is not None
        assert completed.status is JobStatus.COMPLETED
    finally:
        repositories.close()


def test_current_heartbeat_prevents_reclaim() -> None:
    repositories = _repositories()
    try:
        queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        claimed = queue.claim("job-1", "worker-a")
        assert claimed is not None
        _, lease = claimed

        _set_lease_expiry(repositories, timedelta(seconds=1))
        queue.heartbeat(lease)

        assert queue.release_expired() == 0
        assert queue.is_lease_active(lease) is True
    finally:
        repositories.close()


def test_attempt_fencing_rejects_old_attempt() -> None:
    repositories = _repositories()
    try:
        queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        claimed_a = queue.claim("job-1", "worker-a")
        assert claimed_a is not None
        job_a, _ = claimed_a

        _set_lease_expiry(repositories, timedelta(seconds=-1))
        assert queue.release_expired() == 1

        claimed_b = queue.claim("job-1", "worker-b")
        assert claimed_b is not None
        job_b, _ = claimed_b

        assert job_b.attempt == job_a.attempt + 1

        job_a.progress = 0.99
        assert repositories.jobs.update_if_current(
            job_a,
            JobStatus.RUNNING,
            job_a.attempt,
        ) is False

        job_b.progress = 0.50
        assert repositories.jobs.update_if_current(
            job_b,
            JobStatus.RUNNING,
            job_b.attempt,
        ) is True
    finally:
        repositories.close()
