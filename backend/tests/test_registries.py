from backend.app.providers.contracts import ProviderRequest
from backend.app.providers.mock_adapter import MockModelAdapter
from backend.app.providers.registry import ModelRegistry, RegisteredModel
from backend.app.workers.contracts import Worker
from backend.app.workers.registry import WorkerRegistry


class HealthyWorker(Worker):
    name = "healthy"
    def initialize(self): pass
    def health_check(self): return True
    def execute(self, context, parameters): raise NotImplementedError
    def cancel(self, job_id): return True
    def shutdown(self): pass


def test_worker_registry_routes_by_capability():
    registry = WorkerRegistry()
    worker = HealthyWorker()
    registry.register(worker, {"IMAGE"})
    assert registry.find("IMAGE") == [worker]
    assert registry.find("VIDEO") == []


def test_model_registry_routes_healthy_enabled_model():
    registry = ModelRegistry()
    adapter = MockModelAdapter()
    registry.register(RegisteredModel("mock-image", "mock", adapter, priority=10))
    selected = registry.route("IMAGE", "offline")
    assert selected is not None
    assert selected.id == "mock-image"
    response = selected.adapter.execute(ProviderRequest("mock-image", {"prompt": "x"}, seed=1))
    assert response.success is True
