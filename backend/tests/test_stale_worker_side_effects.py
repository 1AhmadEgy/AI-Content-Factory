from app.domain.jobs import GenerationJob, JobStatus, JobType
from app.orchestrator.job_executor import JobExecutor
from app.orchestrator.queue import JobExecutionResult, JobLease, JobQueue, Worker
from app.workers.registry import WorkerRegistry


class ExpiringQueue(JobQueue):
    def __init__(self):
        self.active = True
        self.acknowledged = []

    def enqueue(self, job): pass
    def claim_next(self, worker_id): return None
    def heartbeat(self, lease): pass

    def is_lease_active(self, lease):
        return self.active

    def acknowledge(self, lease, status):
        self.acknowledged.append(status)

    def release_expired(self):
        return 0


class SideEffectWorker(Worker):
    worker_type = "render"

    def __init__(self, side_effects, queue):
        self.side_effects = side_effects
        self.queue = queue
        self.initialized = True

    def initialize(self): self.initialized = True
    def health_check(self): return self.initialized

    def execute(self, job, context):
        # Characterize the current RenderWorker boundary: the worker can persist
        # an output-side effect before JobExecutor performs its final lease check.
        self.side_effects.append({"job_id": job.id, "asset_id": "orphan-asset"})
        self.queue.active = False
        return JobExecutionResult(True, ["orphan-asset"])

    def cancel(self, job_id): pass
    def shutdown(self): self.initialized = False


def test_stale_worker_can_leave_output_side_effect_before_executor_rejects_completion():
    job = GenerationJob(
        id="job-1",
        project_id="project-1",
        type=JobType.VIDEO,
        target_type="render",
        status=JobStatus.RUNNING,
        max_attempts=3,
    )
    job.attempt = 1
    lease = JobLease("job-1", "worker-a", "lease-a", "2099-01-01T00:00:00+00:00")
    queue = ExpiringQueue()
    side_effects = []

    registry = WorkerRegistry()
    registry.register(SideEffectWorker(side_effects, queue), {"VIDEO"}, worker_id="worker-a")

    executor = JobExecutor(
        jobs=type("Jobs", (), {})(),
        queue=queue,
        workers=registry,
    )

    try:
        executor.execute_claimed(job, lease)
    except RuntimeError as exc:
        assert str(exc) == "JOB_LEASE_LOST"
    else:
        raise AssertionError("stale completion must be rejected")

    assert side_effects == [{"job_id": "job-1", "asset_id": "orphan-asset"}]
    assert queue.acknowledged == []
