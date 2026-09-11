from backend.app.providers.contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse
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


class TestAdapter(ModelAdapter):
    def capability(self):
        return ModelCapability("generation", frozenset({"image", "generation"}), runtime="TEST")

    def health_check(self):
        return True

    def execute(self, request):
        return ProviderResponse(True, output_text="test-provider-output", provider_run_id="test-run")

    def cancel(self, provider_run_id):
        return False


def test_worker_registry_routes_by_capability():
    registry = WorkerRegistry()
    worker = HealthyWorker()
    registry.register(worker, {"IMAGE"})
    assert registry.find("IMAGE") == [worker]
    assert registry.find("VIDEO") == []


def test_model_registry_routes_healthy_enabled_model():
    registry = ModelRegistry()
    registry.register(RegisteredModel("test-image", "test", TestAdapter(), priority=10))
    selected = registry.route("generation", "image")
    assert selected is not None
    assert selected.id == "test-image"
    response = selected.adapter.execute(ProviderRequest("test-image", {"prompt": "x"}, seed=1))
    assert response.success is True
