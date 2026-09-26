from __future__ import annotations

import os


class ProviderConfigurationError(RuntimeError):
    """Raised when production provider configuration is incomplete."""


def require_provider_model(env_name: str) -> str:
    """Return an explicitly configured model ID or fail loudly."""
    value = os.getenv(env_name, "").strip()
    if not value:
        raise ProviderConfigurationError(
            f"AI_PROVIDER_CONFIGURATION_ERROR: {env_name} must be explicitly configured"
        )
    return value


def _validate_provider_models(key_env: str, model_envs: tuple[str, ...]) -> None:
    if not os.getenv(key_env, "").strip():
        return
    for name in model_envs:
        require_provider_model(name)


def validate_openai_configuration() -> None:
    _validate_provider_models(
        "OPENAI_API_KEY",
        ("AICF_TEXT_MODEL", "AICF_IMAGE_MODEL", "AICF_TTS_MODEL"),
    )


def validate_gemini_configuration() -> None:
    _validate_provider_models("GEMINI_API_KEY", ("AICF_GEMINI_TEXT_MODEL",))


def validate_anthropic_configuration() -> None:
    _validate_provider_models("ANTHROPIC_API_KEY", ("AICF_ANTHROPIC_TEXT_MODEL",))
