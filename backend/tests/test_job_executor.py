from pathlib import Path
from backend.app.domain.assets import Asset, AssetProvenance, AssetStatus, AssetType, LicenseStatus
from backend.app.domain.job_events import JobEvent
from backend.app.domain.jobs import GenerationJob, JobOutput, JobStatus, JobType
from backend.app.domain.projects import Project
from backend.app.infrastructure.asset_repository import SQLiteAssetRepository
from backend.app.infrastructure.sqlite import SQLiteRepositories
from backend.app.infrastructure.storage import LocalAssetStorage
from backend.app.orchestrator.completion_gate import CompletionGate
from backend.app.orchestrator.job_executor import JobExecutor
from backend.app.orchestrator.queue import JobExecutionResult, JobLease, JobQueue, Worker, WorkerContext
from backend.app.workers.registry import WorkerRegistry

class FakeJobs:
    def __init__(self, job): self.job = job
    def create(self, job): self.job = job; return job
    def get(self, job_id): return self.job if self.job.id == job_id else None
    def update(self, job): self.job = job; return job
class FakeQueue(JobQueue):
    def __init__(self): self.acknowledged = []
    def enqueue(self, job): pass
    def claim_next(self, worker_id): return None
    def heartbeat(self, lease): pass
    def acknowledge(self, lease, status): self.acknowledged.append(status)
    def release_expired(self): return 0
class FakeWorker(Worker):
    worker_type = "fake"
    def __init__(self, result): self.result = result; self.initialized = True
    def initialize(self): self.initialized = True
    def health_check(self): return self.initialized
    def execute(self, job, context): return self.result
    def cancel(self, job_id): pass
    def shutdown(self): self.initialized = False

def make_job(max_attempts=3):
    job = GenerationJob(id="job-1", project_id="project-1", type=JobType.IMAGE, target_type="shot", max_attempts=max_attempts); job.status = JobStatus.RUNNING; job.attempt = 1; return job

def make_lease(): return JobLease("job-1", "worker-1", "lease-1", "2099-01-01T00:00:00+00:00")

def test_executor_persists_success_only_after_completion_gate(tmp_path):
    job = make_job(); jobs, queue = FakeJobs(job), FakeQueue(); registry = WorkerRegistry(); registry.register(FakeWorker(JobExecutionResult(True, ["asset-1"], {"score": 1.0}, "run-1")), {"IMAGE"}, worker_id="worker-1")
    repositories = SQLiteRepositories(":memory:"); repositories.projects.create(Project("project-1", "Test")); storage = LocalAssetStorage(tmp_path / "assets"); assets = SQLiteAssetRepository(repositories.store); digest, path, size = storage.put_bytes(b"fixture")
    assets.create(Asset("asset-1", "project-1", AssetType.IMAGE, path, "text/plain", size, digest, AssetStatus.READY, AssetProvenance(provider="mock", job_id="job-1", license_status=LicenseStatus.VERIFIED)))
    events: list[JobEvent] = []; result = JobExecutor(jobs, queue, registry, events.append, completion_gate=CompletionGate(assets, storage)).execute_claimed(job, make_lease())
    assert result.status is JobStatus.COMPLETED; assert queue.acknowledged == [JobStatus.COMPLETED]; assert [event.event_type for event in events] == ["JOB_STARTED", "JOB_PROGRESS", "JOB_COMPLETED"]; repositories.close()

def test_executor_blocks_when_completion_qc_fails(tmp_path):
    job = make_job(); jobs, queue = FakeJobs(job), FakeQueue(); registry = WorkerRegistry(); registry.register(FakeWorker(JobExecutionResult(True, ["asset-1"], {}, "run-1")), {"IMAGE"}, worker_id="worker-1")
    repositories = SQLiteRepositories(":memory:"); repositories.projects.create(Project("project-1", "Test")); storage = LocalAssetStorage(tmp_path / "assets"); assets = SQLiteAssetRepository(repositories.store); digest, path, size = storage.put_bytes(b"fixture")
    assets.create(Asset("asset-1", "project-1", AssetType.IMAGE, path, "text/plain", size, digest, AssetStatus.READY, AssetProvenance(provider="mock", job_id="job-1", license_status=LicenseStatus.BLOCKED)))
    result = JobExecutor(jobs, queue, registry, completion_gate=CompletionGate(assets, storage)).execute_claimed(job, make_lease())
    assert result.status is JobStatus.BLOCKED; assert jobs.job.status is JobStatus.BLOCKED; assert queue.acknowledged == [JobStatus.BLOCKED]; repositories.close()

def test_executor_retries_retryable_failure_until_limit():
    job = make_job(max_attempts=2); jobs, queue = FakeJobs(job), FakeQueue(); registry = WorkerRegistry(); registry.register(FakeWorker(JobExecutionResult(False, error_code="TIMEOUT", error_message="temporary", retryable=True)), worker_id="worker-1"); result = JobExecutor(jobs, queue, registry).execute_claimed(job, make_lease()); assert result.status is JobStatus.QUEUED; assert result.retried is True; assert queue.acknowledged == [JobStatus.RETRYING]

def test_executor_does_not_retry_non_retryable_failure():
    job = make_job(); jobs, queue = FakeJobs(job), FakeQueue(); registry = WorkerRegistry(); registry.register(FakeWorker(JobExecutionResult(False, error_code="INVALID_INPUT", error_message="bad", retryable=False)), worker_id="worker-1"); result = JobExecutor(jobs, queue, registry).execute_claimed(job, make_lease()); assert result.status is JobStatus.FAILED; assert queue.acknowledged == [JobStatus.FAILED]
