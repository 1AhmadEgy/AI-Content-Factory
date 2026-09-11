from backend.app.domain.job_events import JobEvent
from backend.app.domain.jobs import GenerationJob, JobOutput, JobStatus, JobType
from backend.app.orchestrator.job_executor import JobExecutor
from backend.app.orchestrator.queue import JobExecutionResult, JobLease, JobQueue, Worker
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
    def __init__(self, result): self.result = result; self.initialized = True; self.cancelled = False
    def initialize(self): self.initialized = True
    def health_check(self): return self.initialized
    def execute(self, job, context): return self.result
    def cancel(self, job_id): self.cancelled = True
    def shutdown(self): self.initialized = False


def make_job(max_attempts=3):
    job = GenerationJob(id="job-1", project_id="project-1", type=JobType.IMAGE, target_type="shot", max_attempts=max_attempts)
    job.status = JobStatus.RUNNING
    job.attempt = 1
    return job


def make_lease():
    return JobLease("job-1", "worker-1", "lease-1", "2099-01-01T00:00:00+00:00")


def test_executor_persists_success_and_emits_events():
    job = make_job()
    jobs, queue = FakeJobs(job), FakeQueue()
    worker = FakeWorker(JobExecutionResult(True, ["asset-1"], {"score": 1.0}, "run-1"))
    registry = WorkerRegistry(); registry.register(worker, {"IMAGE"}, worker_id="worker-1")
    events: list[JobEvent] = []
    result = JobExecutor(jobs, queue, registry, events.append).execute_claimed(job, make_lease())
    assert result.status is JobStatus.COMPLETED
    assert jobs.job.output == JobOutput(["asset-1"], {"score": 1.0}, "run-1")
    assert queue.acknowledged == [JobStatus.COMPLETED]
    assert [event.event_type for event in events] == ["JOB_STARTED", "JOB_PROGRESS", "JOB_COMPLETED"]


def test_executor_retries_retryable_failure_until_limit():
    job = make_job(max_attempts=2)
    jobs, queue = FakeJobs(job), FakeQueue()
    worker = FakeWorker(JobExecutionResult(False, error_code="TIMEOUT", error_message="temporary", retryable=True))
    registry = WorkerRegistry(); registry.register(worker, worker_id="worker-1")
    events: list[JobEvent] = []
    result = JobExecutor(jobs, queue, registry, events.append).execute_claimed(job, make_lease())
    assert result.status is JobStatus.QUEUED
    assert result.retried is True
    assert queue.acknowledged == [JobStatus.RETRYING]
    assert events[-1].event_type == "JOB_RETRY_SCHEDULED"


def test_executor_does_not_retry_non_retryable_failure():
    job = make_job(max_attempts=3)
    jobs, queue = FakeJobs(job), FakeQueue()
    worker = FakeWorker(JobExecutionResult(False, error_code="INVALID_INPUT", error_message="bad", retryable=False))
    registry = WorkerRegistry(); registry.register(worker, worker_id="worker-1")
    result = JobExecutor(jobs, queue, registry).execute_claimed(job, make_lease())
    assert result.status is JobStatus.FAILED
    assert queue.acknowledged == [JobStatus.FAILED]
