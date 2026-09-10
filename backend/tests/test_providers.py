from app.providers.builtin import CloudModelAdapter, LocalModelAdapter, MockModelAdapter
from app.providers.contracts import ProviderRequest
from app.providers.registry import RegisteredModel, default_provider_registry


def test_default_registry_routes_mock_capability() -> None:
    registry = default_provider_registry()
    model = registry.route("generation", "image")
    assert model is not None
    assert model.id == "mock-deterministic"
    assert model.provider == "mock"


def test_mock_adapter_is_deterministic_and_offline() -> None:
    adapter = MockModelAdapter()
    request = ProviderRequest("mock-deterministic", {"prompt": "hello"}, seed=7)
    first = adapter.execute(request)
    second = adapter.execute(request)
    assert first.success and second.success
    assert first.provider_run_id == second.provider_run_id
    assert adapter.health_check()


def test_local_and_cloud_adapters_are_transport_neutral() -> None:
    local = LocalModelAdapter("http://localhost:8000", frozenset({"image"}))
    cloud = CloudModelAdapter("example", frozenset({"video"}))
    assert local.capability().runtime == "LOCAL"
    assert cloud.capability().runtime == "CLOUD"
    assert local.health_check() and cloud.health_check()


def test_registry_disable_and_enable() -> None:
    registry = default_provider_registry()
    registry.disable("mock-deterministic")
    assert registry.route("generation", "image") is None
    registry.enable("mock-deterministic")
    assert registry.route("generation", "image") is not None
