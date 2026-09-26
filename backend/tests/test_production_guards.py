from __future__ import annotations

from app.providers.registry import default_provider_registry


def _clear_provider_env(monkeypatch) -> None:
    for name in (
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "ANTHROPIC_API_KEY",
        "AICF_TEXT_MODEL",
        "AICF_IMAGE_MODEL",
        "AICF_TTS_MODEL",
        "AICF_GEMINI_TEXT_MODEL",
        "AICF_ANTHROPIC_TEXT_MODEL",
        "DEEPSEEK_API_KEY",
        "AICF_DEEPSEEK_TEXT_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_production_registry_is_empty_without_real_credentials(monkeypatch) -> None:
    _clear_provider_env(monkeypatch)
    registry = default_provider_registry()
    assert sorted(registry.ids()) == []


def test_production_registry_contains_only_configured_real_providers(monkeypatch) -> None:
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "test-provider-key")
    monkeypatch.setenv("AICF_TEXT_MODEL", "text-test-model")
    monkeypatch.setenv("AICF_IMAGE_MODEL", "image-test-model")
    monkeypatch.setenv("AICF_TTS_MODEL", "tts-test-model")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("AICF_GEMINI_TEXT_MODEL", "gemini-test-model")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("AICF_ANTHROPIC_TEXT_MODEL", "claude-test-model")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("AICF_DEEPSEEK_TEXT_MODEL", "deepseek-test-model")

    registry = default_provider_registry()

    assert registry.ids() == [
        "claude-test-model",
        "deepseek-test-model",
        "gemini-test-model",
        "image-test-model",
        "text-test-model",
        "tts-test-model",
    ]
    assert registry.get("gemini-test-model").provider == "gemini"
    assert registry.get("claude-test-model").provider == "anthropic"
    assert registry.get("deepseek-test-model").provider == "deepseek"
    assert registry.route("generation", "story") is not None
