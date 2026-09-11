from __future__ import annotations

from app.providers.registry import default_provider_registry


def test_production_registry_is_empty_without_real_credentials(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    registry = default_provider_registry()
    assert registry.ids() == []


def test_production_registry_contains_only_configured_real_provider(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-provider-key")
    monkeypatch.setenv("AICF_TEXT_MODEL", "text-test-model")
    monkeypatch.setenv("AICF_IMAGE_MODEL", "image-test-model")
    monkeypatch.setenv("AICF_TTS_MODEL", "tts-test-model")

    registry = default_provider_registry()

    assert registry.ids() == ["image-test-model", "text-test-model", "tts-test-model"]
    assert registry.route("generation", "real-provider") is not None
    assert registry.route("generation", "nonexistent-capability") is None
