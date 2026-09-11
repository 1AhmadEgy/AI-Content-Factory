from __future__ import annotations

import pytest

from app.providers.configuration import ProviderConfigurationError, require_provider_model, validate_openai_configuration


def test_model_configuration_is_required(monkeypatch) -> None:
    monkeypatch.delenv("AICF_TEXT_MODEL", raising=False)
    with pytest.raises(ProviderConfigurationError):
        require_provider_model("AICF_TEXT_MODEL")


def test_openai_configuration_is_optional_without_credentials(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AICF_TEXT_MODEL", raising=False)
    monkeypatch.delenv("AICF_IMAGE_MODEL", raising=False)
    monkeypatch.delenv("AICF_TTS_MODEL", raising=False)
    validate_openai_configuration()


def test_openai_configuration_requires_all_model_ids(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "configured")
    monkeypatch.setenv("AICF_TEXT_MODEL", "text-model")
    monkeypatch.setenv("AICF_IMAGE_MODEL", "image-model")
    monkeypatch.delenv("AICF_TTS_MODEL", raising=False)
    with pytest.raises(ProviderConfigurationError):
        validate_openai_configuration()
