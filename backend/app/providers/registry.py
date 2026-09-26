from __future__ import annotations

import os
from dataclasses import dataclass

from .anthropic_adapter import AnthropicModelAdapter
from .configuration import require_provider_model
from .comfyui_adapter import ComfyUIModelAdapter
from .contracts import ModelAdapter
from .builtin import AIMLAPIModelAdapter, LlamaGenVideoAdapter
from .deepseek_adapter import DeepSeekModelAdapter
from .gemini_adapter import GeminiModelAdapter
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

    def route_candidates(self, category: str, capability: str | None = None) -> list[RegisteredModel]:
        candidates = [m for m in self._models.values() if m.enabled and m.adapter.health_check()]
        candidates = [m for m in candidates if m.adapter.capability().category == category]
        if capability:
            candidates = [m for m in candidates if capability in m.adapter.capability().capabilities]
            if not candidates and capability in {"story", "script", "scene", "shot", "character", "world"}:
                candidates = [
                    m for m in self._models.values()
                    if m.enabled and m.adapter.health_check() and "text" in m.adapter.capability().capabilities
                ]
        return sorted(candidates, key=lambda m: (m.priority, m.id))

    def route(self, category: str, capability: str | None = None) -> RegisteredModel | None:
        candidates = self.route_candidates(category, capability)
        return candidates[0] if candidates else None

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

    if os.getenv("OPENAI_API_KEY", "").strip():
        text_model = require_provider_model("AICF_TEXT_MODEL")
        image_model = require_provider_model("AICF_IMAGE_MODEL")
        tts_model = require_provider_model("AICF_TTS_MODEL")
        registry.register(RegisteredModel(text_model, "openai", OpenAIModelAdapter(text_model, "TEXT"), priority=10))
        registry.register(RegisteredModel(image_model, "openai", OpenAIModelAdapter(image_model, "IMAGE"), priority=10))
        registry.register(RegisteredModel(tts_model, "openai", OpenAIModelAdapter(tts_model, "TTS"), priority=10))

    if os.getenv("GEMINI_API_KEY", "").strip():
        model = require_provider_model("AICF_GEMINI_TEXT_MODEL")
        registry.register(RegisteredModel(model, "gemini", GeminiModelAdapter(model), priority=20))

    if os.getenv("ANTHROPIC_API_KEY", "").strip():
        model = require_provider_model("AICF_ANTHROPIC_TEXT_MODEL")
        registry.register(RegisteredModel(model, "anthropic", AnthropicModelAdapter(model), priority=30))

    if os.getenv("DEEPSEEK_API_KEY", "").strip():
        model = require_provider_model("AICF_DEEPSEEK_TEXT_MODEL")
        registry.register(RegisteredModel(model, "deepseek", DeepSeekModelAdapter(model), priority=40))

    if os.getenv("AIMLAPI_API_KEY", "").strip():
        model = require_provider_model("AICF_AIMLAPI_TEXT_MODEL")
        registry.register(RegisteredModel(model, "aimlapi", AIMLAPIModelAdapter(model), priority=50))

    if os.getenv("AICF_COMFYUI_BASE_URL", "").strip():
        capabilities = frozenset(
            value.strip()
            for value in os.getenv("AICF_COMFYUI_CAPABILITIES", "image,video").split(",")
            if value.strip()
        )
        model_id = os.getenv("AICF_COMFYUI_MODEL", "comfyui-workflow").strip() or "comfyui-workflow"
        registry.register(
            RegisteredModel(
                model_id,
                "comfyui",
                ComfyUIModelAdapter(model_id, capabilities=capabilities),
                priority=55,
            )
        )

    if os.getenv("LLAMAGEN_API_KEY", "").strip():
        video_model = os.getenv("AICF_LLAMAGEN_VIDEO_MODEL", "").strip()
        registry.register(
            RegisteredModel(
                video_model or "llamagen-video",
                "llamagen",
                LlamaGenVideoAdapter(video_model),
                priority=60,
            )
        )

    return registry
