from datetime import datetime, timedelta, timezone

import pytest

from backend.app.domain.jobs import JobInput, JobStatus, JobType
from backend.app.domain.projects import Project
from backend.app.infrastructure.sqlite import SQLiteRepositories
from backend.app.orchestrator.job_service import JobService
from backend.app.orchestrator.runtime import OrchestratorRuntime


def test_stale_worker_cannot_finalize_after_lease_recovery(tmp_path):
    repositories = SQLiteRepositories(":memory:")
    repositories.projects.create(Project(id="project-1", name="Race test"))
    runtime = OrchestratorRuntime(repositories, tmp_path / "assets")
    job = JobService(repositories.jobs).create(
        project_id="project-1",
        job_type=JobType.IMAGE,
        target_type="shot",
        input=JobInput(parameters={"prompt": "race"}, seed=1, deterministic=True),
        max_attempts=3,
    )
    runtime.queue.enqueue(job)
    claimed = runtime.queue.claim_next("mock")
    assert claimed is not None
    stale_job, stale_lease = claimed

    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with repositories.store._lock, repositories.store.connection:
        repositories.store.connection.execute(
            "UPDATE job_leases SET expires_at=? WHERE job_id=? AND lease_id=?",
            (expired, stale_lease.job_id, stale_lease.lease_id),
        )

    assert runtime.recover_expired() == 1
    recovered = repositories.jobs.get(job.id)
    assert recovered is not None
    assert recovered.status is JobStatus.QUEUED
    assert recovered.attempt == 1

    with pytest.raises(RuntimeError, match="JOB_LEASE_LOST"):
        runtime.executor.execute_claimed(stale_job, stale_lease, worker_id="mock")

    persisted = repositories.jobs.get(job.id)
    assert persisted is not None
    assert persisted.status is JobStatus.QUEUED
    assert persisted.attempt == 1
    repositories.close()
