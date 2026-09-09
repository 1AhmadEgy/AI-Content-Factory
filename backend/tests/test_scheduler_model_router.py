from backend.app.orchestrator.model_router import ModelRoute, ModelRouter
from backend.app.orchestrator.scheduler import JobScheduler


def test_model_router_prefers_lowest_priority():
    router = ModelRouter([ModelRoute("mock", "fast", 20), ModelRoute("mock", "stable", 10)])
    assert router.select().model == "stable"


def test_model_router_honors_explicit_model():
    router = ModelRouter([ModelRoute("mock", "fast", 20), ModelRoute("other", "stable", 1)])
    assert router.select(requested_provider="mock", requested_model="fast").model == "fast"


def test_scheduler_does_not_tick_until_started():
    class Queue:
        def claim_next(self):
            raise AssertionError("must not claim while stopped")

    class Executor:
        def execute(self, job):
            raise AssertionError("must not execute while stopped")

    scheduler = JobScheduler(Queue(), Executor())
    assert scheduler.tick().claimed == 0
