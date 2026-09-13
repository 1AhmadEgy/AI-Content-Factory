from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from app.infrastructure.storage import LocalAssetStorage
from app.providers.contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse
from app.providers.registry import ModelRegistry, RegisteredModel
from app.workers.provider_worker import ProviderGenerationWorker


class Adapter(ModelAdapter):
    calls = 0

    def capability(self): return ModelCapability(category="generation", capabilities=frozenset({"generation", "image"}), runtime="TEST")
    def health_check(self): return True
    def execute(self, request: ProviderRequest) -> ProviderResponse:
        type(self).calls += 1
        return ProviderResponse(success=True, output_bytes=b"PNG", output_mime_type="image/png", provider_run_id="provider-1", metrics={})
    def cancel(self, provider_run_id: str) -> bool: return False


class CacheStub:
    def __init__(self, entry): self.entry = entry; self.store = object(); self.released = []
    def get(self, key): return self.entry
    def get_or_lock(self, key, lock_seconds): return self.entry, None
    def release_lock(self, key, token):
        if token is not None:
            self.released.append((key, token))


class BreakerStub:
    def __init__(self, allowed=False): self.allowed = allowed; self.calls = 0
    def acquire(self): self.calls += 1; return self.allowed
    def record_success(self): pass
    def record_failure(self): pass


def _worker(tmp_path: Path):
    registry = ModelRegistry()
    registry.register(RegisteredModel(id="test-image", provider="test", adapter=Adapter(), enabled=True, priority=1))
    worker = ProviderGenerationWorker(registry, LocalAssetStorage(tmp_path), type("Assets", (), {"get": lambda self, _id: None})())
    worker.initialize()
    return worker


def _job(job_id: str) -> GenerationJob:
    return GenerationJob(id=job_id, project_id="p1", type=JobType.IMAGE, target_type="scene", target_id="s1", model="test-image", status=JobStatus.RUNNING, input=JobInput(parameters={"prompt": "sunset"}, seed=42))


def test_cache_hit_ignores_open_circuit(tmp_path: Path):
    worker = _worker(tmp_path)
    worker._cache = CacheStub(SimpleNamespace(output_text=None, output_bytes=b"CACHED", output_mime_type="image/png", output_filename="cached.png", output_metadata={}, metrics={}))
    breaker = BreakerStub(allowed=False)
    worker._breaker = lambda provider, model: breaker
    worker._materialize_response = lambda job, provider, model, response, provider_run_id: ["asset-cache"]
    Adapter.calls = 0

    result = worker.execute(_job("cache-hit"), SimpleNamespace(cancellation_requested=False))

    assert result.success is True
    assert result.asset_ids == ["asset-cache"]
    assert result.metrics["cache_hit"] == 1.0
    assert breaker.calls == 0
    assert Adapter.calls == 0


def test_cache_miss_respects_open_circuit(tmp_path: Path):
    worker = _worker(tmp_path)
    worker._cache = CacheStub(None)
    breaker = BreakerStub(allowed=False)
    worker._breaker = lambda provider, model: breaker
    Adapter.calls = 0

    result = worker.execute(_job("cache-miss"), SimpleNamespace(cancellation_requested=False))

    assert result.success is False
    assert result.error_code == "PROVIDER_CIRCUIT_OPEN"
    assert breaker.calls == 1
    assert Adapter.calls == 0
