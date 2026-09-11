from app.providers.builtin import LocalModelAdapter
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
