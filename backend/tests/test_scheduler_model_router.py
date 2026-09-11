from backend.app.domain.jobs import GenerationJob, JobStatus, JobType
from backend.app.orchestrator.model_router import ModelRoute, ModelRouter
from backend.app.orchestrator.scheduler import JobScheduler
from backend.app.orchestrator.queue import JobLease


def test_model_router_prefers_lowest_priority():
    router = ModelRouter([ModelRoute("mock", "fast", 20), ModelRoute("mock", "stable", 10)])
    assert router.select().model == "stable"


def test_model_router_honors_explicit_model():
    router = ModelRouter([ModelRoute("mock", "fast", 20), ModelRoute("other", "stable", 1)])
    assert router.select(requested_provider="mock", requested_model="fast").model == "fast"


def test_scheduler_does_not_tick_until_started():
    class Queue:
        def claim_next(self, worker_id):
            raise AssertionError("must not claim while stopped")

        def release_expired(self):
            raise AssertionError("must not recover while stopped")

    class Workers:
        def get(self, worker_id):
            raise AssertionError("must not initialize while stopped")

    class Executor:
        workers = Workers()

    scheduler = JobScheduler(Queue(), Executor(), "worker-1")
    assert scheduler.tick().claimed == 0


def test_scheduler_starts_lease_before_executor():
    job = GenerationJob(id="job-1", project_id="project-1", type=JobType.IMAGE, target_type="shot")
    lease = JobLease("job-1", "worker-1", "lease-1", "2099-01-01T00:00:00+00:00")

    class Queue:
        def __init__(self):
            self.started = []
            self.claimed = False

        def release_expired(self):
            return 0

        def claim_next(self, worker_id):
            if self.claimed:
                return None
            self.claimed = True
            job.status = JobStatus.LEASED
            return job, lease

        def start(self, received_lease):
            assert received_lease == lease
            assert job.status is JobStatus.LEASED
            self.started.append(received_lease)
            job.status = JobStatus.RUNNING
            job.attempt += 1
            return job

    class Workers:
        def get(self, worker_id):
            class Worker:
                def initialize(self):
                    pass
                def shutdown(self):
                    pass
            return Worker()

    class Result:
        status = JobStatus.FAILED

    class Executor:
        workers = Workers()
        def execute_claimed(self, received_job, received_lease, worker_id):
            assert received_job.status is JobStatus.RUNNING
            assert received_job.attempt == 1
            assert received_lease == lease
            return Result()

    queue = Queue()
    scheduler = JobScheduler(queue, Executor(), "worker-1")
    scheduler.start()
    stats = scheduler.tick()

    assert stats.claimed == 1
    assert stats.failed == 1
    assert queue.started == [lease]
