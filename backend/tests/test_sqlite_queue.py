from datetime import timedelta

from app.domain.jobs import GenerationJob, JobStatus, JobType, utc_now
from app.domain.projects import Project
from app.infrastructure.sqlite import SQLiteRepositories
from app.infrastructure.sqlite_queue import SQLiteJobQueue


class _FixedRandom:
    def __init__(self, value: float) -> None:
        self.value = value

    def uniform(self, _low: float, _high: float) -> float:
        return self.value


def _queued_job(job_id: str, priority: int, max_attempts: int = 3) -> GenerationJob:
    return GenerationJob(
        id=job_id,
        project_id="project-1",
        type=JobType.IMAGE,
        target_type="shot",
        status=JobStatus.QUEUED,
        priority=priority,
        max_attempts=max_attempts,
    )


def test_claim_orders_by_priority_and_prevents_double_claim() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        repositories.jobs.create(_queued_job("low", 10))
        repositories.jobs.create(_queued_job("high", 100))
        queue = SQLiteJobQueue(repositories.store, repositories.jobs)

        first = queue.claim_next("worker-a")
        second = queue.claim_next("worker-b")

        assert first is not None
        assert first[0].id == "high"
        assert second is not None
        assert second[0].id == "low"
        assert queue.claim_next("worker-c") is None
    finally:
        repositories.close()


def test_retry_is_not_claimable_until_persisted_backoff_expires() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        repositories.jobs.create(_queued_job("job-1", 50))
        queue = SQLiteJobQueue(
            repositories.store,
            repositories.jobs,
            retry_initial_delay_seconds=60,
            retry_max_delay_seconds=300,
            retry_backoff_multiplier=2,
            retry_jitter_ratio=0,
        )
        claimed = queue.claim_next("worker-a")
        assert claimed is not None

        queue.acknowledge(claimed[1], JobStatus.RETRYING)
        assert queue.claim_next("worker-b") is None

        scheduled = repositories.store.connection.execute(
            "SELECT available_at FROM job_retry_schedule WHERE job_id=?", ("job-1",)
        ).fetchone()
        assert scheduled is not None
        assert scheduled["available_at"] > utc_now().isoformat()

        with repositories.store._lock, repositories.store.connection:
            repositories.store.connection.execute(
                "UPDATE job_retry_schedule SET available_at=? WHERE job_id=?",
                ((utc_now() - timedelta(seconds=1)).isoformat(), "job-1"),
            )

        retry_claim = queue.claim_next("worker-b")
        assert retry_claim is not None
        assert retry_claim[0].attempt == 2
    finally:
        repositories.close()


def test_retry_backoff_is_bounded_and_jitter_cannot_exceed_cap() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        queue = SQLiteJobQueue(
            repositories.store,
            repositories.jobs,
            retry_initial_delay_seconds=10,
            retry_max_delay_seconds=25,
            retry_backoff_multiplier=2,
            retry_jitter_ratio=1,
            random_source=_FixedRandom(1000),
        )
        assert queue._retry_delay_seconds(1) == 20
        assert queue._retry_delay_seconds(2) == 25
        assert queue._retry_delay_seconds(10) == 25
    finally:
        repositories.close()


def test_expired_lease_returns_job_to_retrying_with_backoff() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        repositories.jobs.create(_queued_job("job-1", 50))
        queue = SQLiteJobQueue(
            repositories.store,
            repositories.jobs,
            lease_seconds=300,
            retry_initial_delay_seconds=60,
            retry_jitter_ratio=0,
        )
        claimed = queue.claim_next("worker-a")
        assert claimed is not None

        expired = utc_now() - timedelta(seconds=1)
        with repositories.store._lock, repositories.store.connection:
            repositories.store.connection.execute(
                "UPDATE job_leases SET expires_at=? WHERE job_id=?",
                (expired.isoformat(), "job-1"),
            )

        assert queue.release_expired() == 1
        restored = repositories.jobs.get("job-1")
        assert restored is not None
        assert restored.status is JobStatus.RETRYING
        assert restored.error_code == "LEASE_EXPIRED"
        retry_at = repositories.store.connection.execute(
            "SELECT available_at FROM job_retry_schedule WHERE job_id=?", ("job-1",)
        ).fetchone()
        assert retry_at is not None
        assert retry_at["available_at"] > utc_now().isoformat()
    finally:
        repositories.close()


def test_expired_lease_exhausts_retry_budget_without_scheduling_retry() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo"))
        repositories.jobs.create(_queued_job("job-1", 50, max_attempts=1))
        queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        claimed = queue.claim_next("worker-a")
        assert claimed is not None

        expired = utc_now() - timedelta(seconds=1)
        with repositories.store._lock, repositories.store.connection:
            repositories.store.connection.execute(
                "UPDATE job_leases SET expires_at=? WHERE job_id=?",
                (expired.isoformat(), "job-1"),
            )

        assert queue.release_expired() == 1
        restored = repositories.jobs.get("job-1")
        assert restored is not None
        assert restored.status is JobStatus.FAILED
        assert restored.error_code == "LEASE_EXPIRED"
        assert repositories.store.connection.execute(
            "SELECT 1 FROM job_retry_schedule WHERE job_id=?", ("job-1",)
        ).fetchone() is None
    finally:
        repositories.close()
