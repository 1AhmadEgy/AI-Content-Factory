from datetime import timedelta
from backend.app.domain.jobs import GenerationJob, JobStatus, JobType, utc_now
from backend.app.domain.projects import Project
from backend.app.infrastructure.sqlite import SQLiteRepositories
from backend.app.infrastructure.sqlite_queue import SQLiteJobQueue

def _queued_job(job_id: str, priority: int) -> GenerationJob:
    return GenerationJob(id=job_id, project_id="project-1", type=JobType.IMAGE, target_type="shot", status=JobStatus.QUEUED, priority=priority)

def test_claim_orders_by_priority_and_prevents_double_claim() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo")); repositories.jobs.create(_queued_job("low", 10)); repositories.jobs.create(_queued_job("high", 100)); queue = SQLiteJobQueue(repositories.store, repositories.jobs)
        first = queue.claim_next("worker-a"); second = queue.claim_next("worker-b")
        assert first is not None and first[0].id == "high"; assert second is not None and second[0].id == "low"; assert queue.claim_next("worker-c") is None
    finally: repositories.close()

def test_expired_lease_returns_job_to_retry_queue() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        repositories.projects.create(Project(id="project-1", name="Demo")); repositories.jobs.create(_queued_job("job-1", 50)); queue = SQLiteJobQueue(repositories.store, repositories.jobs, lease_seconds=300); assert queue.claim_next("worker-a") is not None
        expired = utc_now() - timedelta(seconds=1)
        with repositories.store._lock, repositories.store.connection:
            repositories.store.connection.execute("UPDATE job_leases SET expires_at=? WHERE job_id=?", (expired.isoformat(), "job-1"))
        assert queue.release_expired() == 1
        restored = repositories.jobs.get("job-1")
        assert restored is not None and restored.status is JobStatus.QUEUED and restored.error_code == "LEASE_EXPIRED"
    finally: repositories.close()
