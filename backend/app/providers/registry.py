from __future__ import annotations

import os
from dataclasses import dataclass

from .builtin import GeminiModelAdapter, LocalMediaModelAdapter, LocalModelAdapter, OpenAICompatibleCloudAdapter
from .contracts import ModelAdapter


@dataclass(frozen=True, slots=True)
class RegisteredModel:
    id: str
    provider: str
    adapter: ModelAdapter
    enabled: bool = True
    priority: int = 100


class ModelRegistry:
    """Provider-agnostic registry; unavailable providers are never replaced by fake output."""

    def __init__(self) -> None:
        self._models: dict[str, RegisteredModel] = {}

    def register(self, model: RegisteredModel) -> None:
        if model.id in self._models:
            raise ValueError(f"Model already registered: {model.id}")
        self._models[model.id] = model

    def get(self, model_id: str) -> RegisteredModel:
        return self._models[model_id]

    def route(self, category: str, capability: str | None = None) -> RegisteredModel | None:
        candidates = [m for m in self._models.values() if m.enabled and m.adapter.health_check()]
        candidates = [m for m in candidates if m.adapter.capability().category == category]
        if capability:
            candidates = [m for m in candidates if capability in m.adapter.capability().capabilities]
        return min(candidates, key=lambda m: (m.priority, m.id), default=None)

    def ids(self) -> list[str]:
        return sorted(self._models)

    def disable(self, model_id: str) -> None:
        model = self.get(model_id)
        self._models[model_id] = RegisteredModel(model.id, model.provider, model.adapter, False, model.priority)

    def enable(self, model_id: str) -> None:
        model = self.get(model_id)
        self._models[model_id] = RegisteredModel(model.id, model.provider, model.adapter, True, model.priority)


def _capabilities(raw: str, default: frozenset[str]) -> frozenset[str]:
    values = frozenset(item.strip().lower() for item in raw.split(",") if item.strip())
    return values or default


def default_provider_registry() -> ModelRegistry:
    """Build the registry exclusively from explicitly configured real provider endpoints/keys."""
    registry = ModelRegistry()

    text_endpoint = os.getenv("AICF_TEXT_PROVIDER_ENDPOINT", "").strip()
    text_model = os.getenv("AICF_TEXT_PROVIDER_MODEL", "").strip()
    if text_endpoint and text_model and text_model != "your-text-model":
        registry.register(
            RegisteredModel(
                id=text_model,
                provider=os.getenv("AICF_TEXT_PROVIDER_NAME", "local-text"),
                adapter=LocalModelAdapter(text_endpoint, _capabilities(os.getenv("AICF_TEXT_PROVIDER_CAPABILITIES", "story,script,scene,shot"), frozenset({"story", "script", "scene", "shot"})), timeout_seconds=int(os.getenv("AICF_TEXT_PROVIDER_TIMEOUT_SECONDS", "120"))),
                priority=int(os.getenv("AICF_TEXT_PROVIDER_PRIORITY", "50")),
            )
        )

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    if gemini_key and gemini_model:
        registry.register(
            RegisteredModel(
                id=f"gemini:{gemini_model}",
                provider="gemini",
                adapter=GeminiModelAdapter(gemini_key, gemini_model, _capabilities(os.getenv("GEMINI_CAPABILITIES", "story,script,scene,shot,character,world,text"), frozenset({"story", "script", "scene", "shot", "character", "world", "text"})), timeout_seconds=int(os.getenv("GEMINI_TIMEOUT_SECONDS", "120"))),
                priority=int(os.getenv("GEMINI_PRIORITY", "40")),
            )
        )

    hf_token = os.getenv("HF_TOKEN", "").strip()
    hf_model = os.getenv("HF_MODEL", "").strip()
    hf_endpoint = os.getenv("HF_ENDPOINT", "https://router.huggingface.co").strip()
    if hf_token and hf_model and hf_endpoint:
        registry.register(
            RegisteredModel(
                id=f"huggingface:{hf_model}",
                provider="huggingface",
                adapter=OpenAICompatibleCloudAdapter(hf_endpoint, hf_token, _capabilities(os.getenv("HF_CAPABILITIES", "story,script,scene,shot,character,world,text"), frozenset({"story", "script", "scene", "shot", "character", "world", "text"})), timeout_seconds=int(os.getenv("HF_TIMEOUT_SECONDS", "120"))),
                priority=int(os.getenv("HF_PRIORITY", "60")),
            )
        )

    media_endpoint = os.getenv("AICF_MEDIA_PROVIDER_ENDPOINT", "").strip()
    media_model = os.getenv("AICF_MEDIA_PROVIDER_MODEL", "").strip()
    if media_endpoint and media_model:
        registry.register(
            RegisteredModel(
                id=media_model,
                provider=os.getenv("AICF_MEDIA_PROVIDER_NAME", "local-media"),
                adapter=LocalMediaModelAdapter(media_endpoint, _capabilities(os.getenv("AICF_MEDIA_PROVIDER_CAPABILITIES", "image,video,tts,music,sfx,lipsync,upscale,interpolation"), frozenset({"image", "video", "tts", "music", "sfx", "lipsync", "upscale", "interpolation"})), timeout_seconds=int(os.getenv("AICF_MEDIA_PROVIDER_TIMEOUT_SECONDS", "300"))),
                priority=int(os.getenv("AICF_MEDIA_PROVIDER_PRIORITY", "50")),
            )
        )

    return registry
