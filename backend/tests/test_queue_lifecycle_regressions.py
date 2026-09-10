from datetime import datetime, timedelta, timezone

from backend.app.domain.jobs import JobInput, JobStatus, JobType
from backend.app.domain.projects import Project
from backend.app.infrastructure.sqlite import SQLiteRepositories
from backend.app.orchestrator.job_service import JobService
from backend.app.orchestrator.queue import JobExecutionResult, Worker
from backend.app.orchestrator.runtime import OrchestratorRuntime


class RetryWorker(Worker):
    worker_type = "retry-test"

    def initialize(self):
        pass

    def health_check(self):
        return True

    def execute(self, job, context):
        return JobExecutionResult(
            success=False,
            error_code="TEMPORARY_FAILURE",
            error_message="temporary provider failure",
            retryable=True,
        )

    def cancel(self, job_id):
        pass

    def shutdown(self):
        pass


def _runtime_with_job(tmp_path, max_attempts=3):
    repositories = SQLiteRepositories(":memory:")
    repositories.projects.create(Project(id="project-1", name="Queue lifecycle"))
    runtime = OrchestratorRuntime(repositories, tmp_path / "assets")
    job = JobService(repositories.jobs).create(
        project_id="project-1",
        job_type=JobType.IMAGE,
        target_type="shot",
        input=JobInput(parameters={"prompt": "queue"}, deterministic=True),
        max_attempts=max_attempts,
    )
    runtime.queue.enqueue(job)
    return repositories, runtime, job


def test_retryable_execution_requeues_same_job_without_duplicate_lease(tmp_path):
    repositories, runtime, job = _runtime_with_job(tmp_path, max_attempts=3)
    runtime.workers.register(RetryWorker(), {"IMAGE"}, worker_id="retry-test")

    result = runtime.execute_job(job.id, "retry-test")

    assert result is not None
    assert result.status is JobStatus.QUEUED
    assert result.retried is True
    persisted = repositories.jobs.get(job.id)
    assert persisted is not None
    assert persisted.status is JobStatus.QUEUED
    assert persisted.attempt == 1
    lease = repositories.store.connection.execute(
        "SELECT * FROM job_leases WHERE job_id=?", (job.id,)
    ).fetchone()
    assert lease is None

    next_claim = runtime.queue.claim(job.id, "retry-test")
    assert next_claim is not None
    assert next_claim[0].attempt == 2
    repositories.close()


def test_expired_lease_exhausts_retry_budget_and_becomes_failed(tmp_path):
    repositories, runtime, job = _runtime_with_job(tmp_path, max_attempts=1)
    claimed = runtime.queue.claim(job.id, "mock")
    assert claimed is not None
    _, lease = claimed

    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with repositories.store._lock, repositories.store.connection:
        repositories.store.connection.execute(
            "UPDATE job_leases SET expires_at=? WHERE job_id=? AND lease_id=?",
            (expired, lease.job_id, lease.lease_id),
        )

    assert runtime.recover_expired() == 1
    persisted = repositories.jobs.get(job.id)
    assert persisted is not None
    assert persisted.status is JobStatus.FAILED
    assert persisted.attempt == 1
    assert persisted.error_code == "LEASE_EXPIRED"
    assert runtime.queue.claim(job.id, "mock") is None
    assert repositories.store.connection.execute(
        "SELECT 1 FROM job_leases WHERE job_id=?", (job.id,)
    ).fetchone() is None
    repositories.close()
