from app.domain.jobs import JobType
from app.orchestrator.queue import JobExecutionResult, WorkerContext
from app.providers.builtin import LlamaGenVideoAdapter, LocalModelAdapter
from app.providers.runway_adapter import RunwayVideoAdapter
from app.workers.provider_worker import ProviderGenerationWorker
from app.providers.contracts import ProviderRequest
from app.providers.openai_adapter import OpenAIModelAdapter
from app.providers.registry import ModelRegistry, RegisteredModel, default_provider_registry


def test_default_registry_requires_real_provider_configuration() -> None:
    registry = default_provider_registry()
    assert registry.ids() == [] or all(registry.get(model_id).provider == "openai" for model_id in registry.ids())


def test_local_adapter_is_transport_real() -> None:
    adapter = LocalModelAdapter("http://localhost:8000", frozenset({"text"}))
    request = ProviderRequest("local-model", {"prompt": "hello"}, seed=7)
    assert adapter.capability().runtime == "LOCAL"
    assert adapter.health_check()
    assert request.model == "local-model"


def test_openai_adapter_requires_credentials_without_synthetic_output() -> None:
    adapter = OpenAIModelAdapter("configured-model", "TEXT", api_key="")
    response = adapter.execute(ProviderRequest("configured-model", {"prompt": "hello"}))
    assert not response.success
    assert response.error_code == "OPENAI_API_KEY_MISSING"
    assert response.output_text is None


def test_registry_disable_and_enable() -> None:
    registry = ModelRegistry()
    adapter = LocalModelAdapter("http://localhost:8000", frozenset({"text"}))
    registry.register(RegisteredModel("local-text", "local", adapter, priority=10))
    assert registry.route("generation", "text") is not None
    registry.disable("local-text")
    assert registry.route("generation", "text") is None
    registry.enable("local-text")
    assert registry.route("generation", "text") is not None



def test_registry_route_candidates_are_priority_ordered() -> None:
    registry = ModelRegistry()
    first = LocalModelAdapter("http://localhost:8001", frozenset({"text"}))
    second = LocalModelAdapter("http://localhost:8002", frozenset({"text"}))
    registry.register(RegisteredModel("second", "local", second, priority=20))
    registry.register(RegisteredModel("first", "local", first, priority=10))
    assert [model.id for model in registry.route_candidates("generation", "text")] == ["first", "second"]


def test_runway_adapter_requires_credentials_without_network_call() -> None:
    adapter = RunwayVideoAdapter("gen4.5", api_key="")
    response = adapter.execute(ProviderRequest("gen4.5", {"prompt": "test"}))
    assert not response.success
    assert response.error_code == "RUNWAY_API_KEY_MISSING"


def test_llamagen_adapter_requires_credentials_without_network_call() -> None:
    adapter = LlamaGenVideoAdapter("video-model", api_key="")
    response = adapter.execute(ProviderRequest("video-model", {"prompt": "test"}))
    assert not response.success
    assert response.error_code == "LLAMAGEN_API_KEY_MISSING"


def _fallback_worker() -> ProviderGenerationWorker:
    registry = ModelRegistry()
    registry.register(RegisteredModel("first", "local", LocalModelAdapter("http://localhost:8001", frozenset({"text", "story"})), priority=10))
    registry.register(RegisteredModel("second", "local", LocalModelAdapter("http://localhost:8002", frozenset({"text", "story"})), priority=20))
    worker = ProviderGenerationWorker(registry, storage=None, assets=None)  # type: ignore[arg-type]
    worker._initialized = True
    return worker


def _story_job():
    return type("Job", (), {"model": None, "type": JobType.STORY})()


def test_worker_falls_back_after_retryable_provider_failure() -> None:
    worker = _fallback_worker()
    attempts: list[str] = []

    def fake_execute(job, capability, model):
        attempts.append(model.id)
        if model.id == "first":
            return JobExecutionResult(False, error_code="TEMPORARY", retryable=True)
        return JobExecutionResult(True, asset_ids=["asset-2"])

    worker._execute_model = fake_execute  # type: ignore[method-assign]
    result = worker.execute(_story_job(), WorkerContext("worker", "lease"))

    assert result.success
    assert attempts == ["first", "second"]
    assert result.asset_ids == ["asset-2"]


def test_worker_stops_after_permanent_provider_failure() -> None:
    worker = _fallback_worker()
    attempts: list[str] = []

    def fake_execute(job, capability, model):
        attempts.append(model.id)
        return JobExecutionResult(False, error_code="PERMANENT", retryable=False)

    worker._execute_model = fake_execute  # type: ignore[method-assign]
    result = worker.execute(_story_job(), WorkerContext("worker", "lease"))

    assert not result.success
    assert attempts == ["first"]
    assert result.error_code == "PERMANENT"
