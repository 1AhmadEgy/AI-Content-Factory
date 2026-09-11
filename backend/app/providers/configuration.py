from __future__ import annotations

import os


class ProviderConfigurationError(RuntimeError):
    """Raised when production provider configuration is incomplete."""


def require_provider_model(env_name: str) -> str:
    """Return an explicitly configured model ID or fail loudly.

    Production must never invent a model ID when credentials are present.
    """
    value = os.getenv(env_name, "").strip()
    if not value:
        raise ProviderConfigurationError(
            f"AI_PROVIDER_CONFIGURATION_ERROR: {env_name} must be explicitly configured"
        )
    return value


def validate_openai_configuration() -> None:
    """Validate the complete OpenAI production configuration when enabled."""
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return
    for name in ("AICF_TEXT_MODEL", "AICF_IMAGE_MODEL", "AICF_TTS_MODEL"):
        require_provider_model(name)
