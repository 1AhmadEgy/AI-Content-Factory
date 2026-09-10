from datetime import datetime, timedelta, timezone

import pytest

from backend.app.domain.jobs import JobInput, JobStatus, JobType
from backend.app.domain.projects import Project
from backend.app.infrastructure.sqlite import SQLiteRepositories
from backend.app.orchestrator.job_service import JobService
from backend.app.orchestrator.queue import JobLease
from backend.app.orchestrator.runtime import OrchestratorRuntime


def _queued_claim(tmp_path):
    repositories = SQLiteRepositories(":memory:")
    repositories.projects.create(Project(id="project-1", name="Race test"))
    runtime = OrchestratorRuntime(repositories, tmp_path / "assets")
    job = JobService(repositories.jobs).create(
        project_id="project-1", job_type=JobType.IMAGE, target_type="shot",
        input=JobInput(parameters={"prompt": "race"}, seed=1, deterministic=True), max_attempts=3,
    )
    runtime.queue.enqueue(job)
    claimed = runtime.queue.claim_next("mock")
    assert claimed is not None
    return repositories, runtime, job, claimed


def test_stale_worker_cannot_finalize_after_lease_recovery(tmp_path):
    repositories, runtime, job, claimed = _queued_claim(tmp_path)
    stale_job, stale_lease = claimed
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with repositories.store._lock, repositories.store.connection:
        repositories.store.connection.execute(
            "UPDATE job_leases SET expires_at=? WHERE job_id=? AND lease_id=?",
            (expired, stale_lease.job_id, stale_lease.lease_id),
        )
    assert runtime.recover_expired() == 1
    recovered = repositories.jobs.get(job.id)
    assert recovered is not None and recovered.status is JobStatus.QUEUED
    assert recovered.attempt == 1
    with pytest.raises(RuntimeError, match="JOB_LEASE_LOST"):
        runtime.executor.execute_claimed(stale_job, stale_lease, worker_id="mock")
    persisted = repositories.jobs.get(job.id)
    assert persisted is not None and persisted.status is JobStatus.QUEUED
    assert persisted.attempt == 1
    repositories.close()


def test_lease_worker_identity_is_required_for_heartbeat(tmp_path):
    repositories, runtime, _job, claimed = _queued_claim(tmp_path)
    _stale_job, lease = claimed
    forged = JobLease(lease.job_id, "other-worker", lease.lease_id, lease.expires_at)
    with pytest.raises(KeyError, match="JOB_LEASE_NOT_FOUND"):
        runtime.queue.heartbeat(forged)
    assert runtime.queue.is_lease_active(lease) is True
    repositories.close()


def test_recovered_job_can_be_claimed_once_by_new_worker(tmp_path):
    repositories, runtime, job, claimed = _queued_claim(tmp_path)
    _stale_job, stale_lease = claimed
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    with repositories.store._lock, repositories.store.connection:
        repositories.store.connection.execute(
            "UPDATE job_leases SET expires_at=? WHERE job_id=? AND lease_id=?",
            (expired, stale_lease.job_id, stale_lease.lease_id),
        )
    assert runtime.recover_expired() == 1
    replacement = runtime.queue.claim(job.id, "mock")
    assert replacement is not None
    replacement_job, replacement_lease = replacement
    assert replacement_job.status is JobStatus.RUNNING
    assert replacement_job.attempt == 2
    assert replacement_lease.lease_id != stale_lease.lease_id
    assert runtime.queue.claim(job.id, "mock") is None
    repositories.close()
