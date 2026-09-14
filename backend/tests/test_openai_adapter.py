import json

from app.providers.openai_adapter import OpenAIModelAdapter
from app.providers.contracts import ProviderRequest


def test_openai_adapter_never_fabricates_without_credentials(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    adapter = OpenAIModelAdapter("gpt-5.6-luna", "TEXT")
    response = adapter.execute(ProviderRequest("gpt-5.6-luna", {"prompt": "hello"}))
    assert response.success is False
    assert response.error_code == "OPENAI_API_KEY_MISSING"
    assert response.output_text is None


def test_openai_adapter_health_requires_credentials(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert OpenAIModelAdapter("gpt-5.6-luna", "TEXT").health_check() is False


def test_openai_adapter_sends_idempotency_key(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"id": "resp_123", "output_text": "hello"}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["headers"] = dict(request.header_items())
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    adapter = OpenAIModelAdapter("gpt-5.6-luna", "TEXT", api_key="test-key")
    response = adapter.execute(
        ProviderRequest(
            "gpt-5.6-luna",
            {"prompt": "hello"},
            idempotency_key="cache-key-123",
        )
    )

    assert response.success is True
    assert response.provider_run_id == "resp_123"
    assert captured["headers"]["Idempotency-key"] == "cache-key-123"
