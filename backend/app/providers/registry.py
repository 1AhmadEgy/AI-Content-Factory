from __future__ import annotations

import os
from dataclasses import dataclass

from .configuration import require_provider_model
from .contracts import ModelAdapter
from .openai_adapter import OpenAIModelAdapter


@dataclass(frozen=True, slots=True)
class RegisteredModel:
    id: str
    provider: str
    adapter: ModelAdapter
    enabled: bool = True
    priority: int = 100


class ModelRegistry:
    """Provider-agnostic registry. Only configured, real providers are routable."""

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
            if not candidates and capability in {"story", "script", "scene", "shot", "character", "world"}:
                candidates = [m for m in self._models.values() if m.enabled and m.adapter.health_check() and "text" in m.adapter.capability().capabilities]
        return min(candidates, key=lambda m: (m.priority, m.id), default=None)

    def ids(self) -> list[str]:
        return sorted(self._models)

    def disable(self, model_id: str) -> None:
        model = self.get(model_id)
        self._models[model_id] = RegisteredModel(model.id, model.provider, model.adapter, False, model.priority)

    def enable(self, model_id: str) -> None:
        model = self.get(model_id)
        self._models[model_id] = RegisteredModel(model.id, model.provider, model.adapter, True, model.priority)


def default_provider_registry() -> ModelRegistry:
    """Build the production registry from explicit environment configuration."""
    registry = ModelRegistry()
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return registry
    text_model = require_provider_model("AICF_TEXT_MODEL")
    image_model = require_provider_model("AICF_IMAGE_MODEL")
    tts_model = require_provider_model("AICF_TTS_MODEL")
    registry.register(RegisteredModel(text_model, "openai", OpenAIModelAdapter(text_model, "TEXT"), priority=10))
    registry.register(RegisteredModel(image_model, "openai", OpenAIModelAdapter(image_model, "IMAGE"), priority=10))
    registry.register(RegisteredModel(tts_model, "openai", OpenAIModelAdapter(tts_model, "TTS"), priority=10))
    return registry
