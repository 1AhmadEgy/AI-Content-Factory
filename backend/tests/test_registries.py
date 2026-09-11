from backend.app.providers.builtin import LocalMediaModelAdapter, LocalModelAdapter
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


def test_real_provider_adapters_expose_generation_capabilities():
    registry = ModelRegistry()
    text = LocalModelAdapter("http://127.0.0.1:11434", frozenset({"story", "script"}))
    media = LocalMediaModelAdapter("http://127.0.0.1:8188", frozenset({"image", "video"}))
    registry.register(RegisteredModel("text", "local-text", text, priority=10))
    registry.register(RegisteredModel("media", "local-media", media, priority=20))
    assert registry.get("text").adapter.capability().category == "generation"
    assert "story" in registry.get("text").adapter.capability().capabilities
    assert "image" in registry.get("media").adapter.capability().capabilities
