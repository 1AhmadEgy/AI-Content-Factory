from types import SimpleNamespace

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


class StagedRenderWorker(Worker):
    worker_type = "render"

    def __init__(self, queue):
        self.queue = queue
        self.initialized = True

    def initialize(self): self.initialized = True
    def health_check(self): return self.initialized

    def execute(self, job, context):
        # The worker only returns a staged output. It does not persist Asset metadata.
        self.queue.active = False
        return JobExecutionResult(
            True,
            pending_assets=[SimpleNamespace(id="staged-asset")],
        )

    def cancel(self, job_id): pass
    def shutdown(self): self.initialized = False


def test_stale_render_cannot_commit_pending_asset_after_lease_loss():
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
    committed = []

    registry = WorkerRegistry()
    registry.register(StagedRenderWorker(queue), {"VIDEO"}, worker_id="worker-a")

    def commit_pending_assets(job, lease, assets):
        committed.extend(asset.id for asset in assets)
        return [asset.id for asset in assets]

    executor = JobExecutor(
        jobs=type("Jobs", (), {})(),
        queue=queue,
        workers=registry,
        commit_pending_assets=commit_pending_assets,
    )

    try:
        executor.execute_claimed(job, lease)
    except RuntimeError as exc:
        assert str(exc) == "JOB_LEASE_LOST"
    else:
        raise AssertionError("stale completion must be rejected")

    assert committed == []
    assert queue.acknowledged == []
