from app.providers.builtin import CloudModelAdapter, LocalMediaModelAdapter, LocalModelAdapter
from app.providers.registry import RegisteredModel, ModelRegistry, default_provider_registry


def test_default_registry_has_no_implicit_provider() -> None:
    registry = default_provider_registry()
    assert registry.ids() == []
    assert registry.route("generation", "image") is None


def test_local_and_cloud_adapters_are_explicit_transports() -> None:
    local = LocalModelAdapter("http://localhost:8000", frozenset({"story"}))
    media = LocalMediaModelAdapter("http://localhost:9000/generate", frozenset({"image"}))
    cloud = CloudModelAdapter("example", frozenset({"video"}))
    assert local.capability().runtime == "LOCAL"
    assert media.capability().runtime == "LOCAL"
    assert cloud.capability().runtime == "CLOUD"
    assert local.health_check() and media.health_check() and cloud.health_check()


def test_registry_disable_and_enable() -> None:
    registry = ModelRegistry()
    registry.register(RegisteredModel("text", "local-text", LocalModelAdapter("http://localhost:8000", frozenset({"story"}))))
    assert registry.route("generation", "story") is not None
    registry.disable("text")
    assert registry.route("generation", "story") is None
    registry.enable("text")
    assert registry.route("generation", "story") is not None
