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
