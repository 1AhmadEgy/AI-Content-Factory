from __future__ import annotations

import json

from app.providers.builtin import CloudModelAdapter, LocalMediaModelAdapter, LocalModelAdapter
from app.providers.contracts import ProviderRequest
from app.providers.registry import RegisteredModel, ModelRegistry, default_provider_registry


class _Response:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


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


def test_local_text_adapter_rejects_success_without_provider_run_id(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.providers.builtin.urlopen",
        lambda *args, **kwargs: _Response({"choices": [{"message": {"content": "hello"}}]}),
    )
    adapter = LocalModelAdapter("http://localhost:8000", frozenset({"story"}))
    response = adapter.execute(ProviderRequest("local-model", {"prompt": "hello"}))
    assert response.success is False
    assert response.error_code == "LOCAL_PROVIDER_RUN_ID_MISSING"


def test_registry_disable_and_enable() -> None:
    registry = ModelRegistry()
    registry.register(RegisteredModel("text", "local-text", LocalModelAdapter("http://localhost:8000", frozenset({"story"}))))
    assert registry.route("generation", "story") is not None
    registry.disable("text")
    assert registry.route("generation", "story") is None
    registry.enable("text")
    assert registry.route("generation", "story") is not None
