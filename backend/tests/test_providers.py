from app.domain.jobs import JobType
from app.orchestrator.queue import JobExecutionResult, WorkerContext
from app.providers.builtin import LlamaGenVideoAdapter, LocalModelAdapter
from app.providers.comfyui_adapter import ComfyUIModelAdapter
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


def test_comfyui_adapter_requires_workflow_without_network_call() -> None:
    adapter = ComfyUIModelAdapter("comfy", base_url="http://127.0.0.1:8188")
    response = adapter.execute(ProviderRequest("comfy", {"prompt": "test"}))
    assert not response.success
    assert response.error_code == "COMFYUI_WORKFLOW_REQUIRED"


def test_comfyui_adapter_applies_safe_node_input_overrides() -> None:
    adapter = ComfyUIModelAdapter("comfy", base_url="http://127.0.0.1:8188")
    workflow = {"1": {"class_type": "CLIPTextEncode", "inputs": {"text": "old"}}}
    captured: list[dict] = []

    def fake_request(method, path, payload, headers):
        captured.append(payload or {})
        if method == "POST":
            return {"prompt_id": "test-prompt"}
        return {"test-prompt": {"status": {"status_str": "success"}, "outputs": {"9": {"images": [{"filename": "x.png"}]}}}}

    adapter._request_json = fake_request  # type: ignore[method-assign]
    adapter._collect_outputs = lambda outputs, headers: (b"image", "image/png", "x.png", {})  # type: ignore[method-assign]
    adapter.timeout_seconds = 1
    adapter.poll_interval_seconds = 0.2
    response = adapter.execute(
        ProviderRequest(
            "comfy",
            {"workflow": workflow, "prompt_inputs": {"1.text": "new"}},
        )
    )
    assert response.success
    assert response.provider_run_id == "test-prompt"
    assert captured[0]["prompt"]["1"]["inputs"]["text"] == "new"
    assert workflow["1"]["inputs"]["text"] == "old"
