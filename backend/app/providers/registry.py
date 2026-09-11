from __future__ import annotations

import os
from dataclasses import dataclass

from .builtin import LocalMediaModelAdapter, LocalModelAdapter
from .contracts import ModelAdapter, ModelCapability


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
    """Build the registry exclusively from explicitly configured real provider endpoints."""
    registry = ModelRegistry()

    text_endpoint = os.getenv("AICF_TEXT_PROVIDER_ENDPOINT", "").strip()
    text_model = os.getenv("AICF_TEXT_PROVIDER_MODEL", "").strip()
    if text_endpoint and text_model:
        registry.register(
            RegisteredModel(
                id=text_model,
                provider=os.getenv("AICF_TEXT_PROVIDER_NAME", "local-text"),
                adapter=LocalModelAdapter(
                    text_endpoint,
                    _capabilities(
                        os.getenv("AICF_TEXT_PROVIDER_CAPABILITIES", "story,script,scene,shot"),
                        frozenset({"story", "script", "scene", "shot"}),
                    ),
                    timeout_seconds=int(os.getenv("AICF_TEXT_PROVIDER_TIMEOUT_SECONDS", "120")),
                ),
                priority=int(os.getenv("AICF_TEXT_PROVIDER_PRIORITY", "50")),
            )
        )

    media_endpoint = os.getenv("AICF_MEDIA_PROVIDER_ENDPOINT", "").strip()
    media_model = os.getenv("AICF_MEDIA_PROVIDER_MODEL", "").strip()
    if media_endpoint and media_model:
        registry.register(
            RegisteredModel(
                id=media_model,
                provider=os.getenv("AICF_MEDIA_PROVIDER_NAME", "local-media"),
                adapter=LocalMediaModelAdapter(
                    media_endpoint,
                    _capabilities(
                        os.getenv("AICF_MEDIA_PROVIDER_CAPABILITIES", "image,video,tts,music,sfx,lipsync,upscale,interpolation"),
                        frozenset({"image", "video", "tts", "music", "sfx", "lipsync", "upscale", "interpolation"}),
                    ),
                    timeout_seconds=int(os.getenv("AICF_MEDIA_PROVIDER_TIMEOUT_SECONDS", "300")),
                ),
                priority=int(os.getenv("AICF_MEDIA_PROVIDER_PRIORITY", "50")),
            )
        )

    return registry
