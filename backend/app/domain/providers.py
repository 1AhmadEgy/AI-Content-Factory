from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderKind(str, Enum):
    MOCK = "mock"
    LOCAL = "local"
    CLOUD = "cloud"


class Capability(str, Enum):
    STORY = "story"
    IMAGE = "image"
    VIDEO = "video"
    TTS = "tts"
    MUSIC = "music"
    SFX = "sfx"
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"
    QC = "qc"
    RENDER = "render"


@dataclass(slots=True, frozen=True)
class ModelSpec:
    id: str
    provider: str
    display_name: str
    capabilities: frozenset[Capability]
    quality: float = 0.5
    speed: float = 0.5
    cost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities


@dataclass(slots=True, frozen=True)
class ProviderSpec:
    id: str
    display_name: str
    kind: ProviderKind
    models: tuple[ModelSpec, ...] = ()
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def model(self, model_id: str) -> ModelSpec | None:
        return next((model for model in self.models if model.id == model_id), None)


@dataclass(slots=True, frozen=True)
class ModelSelection:
    provider: ProviderSpec
    model: ModelSpec
    score: float


class ProviderError(RuntimeError):
    pass


class ProviderRegistry:
    """In-memory registry used by the backend; persistence can be layered later."""

    def __init__(self, providers: list[ProviderSpec] | None = None) -> None:
        self._providers: dict[str, ProviderSpec] = {}
        for provider in providers or []:
            self.register(provider)

    def register(self, provider: ProviderSpec) -> None:
        if not provider.id.strip():
            raise ValueError("provider id must not be empty")
        self._providers[provider.id] = provider

    def get(self, provider_id: str) -> ProviderSpec | None:
        return self._providers.get(provider_id)

    def all(self) -> tuple[ProviderSpec, ...]:
        return tuple(self._providers.values())

    def select(
        self,
        capability: Capability,
        provider_id: str | None = None,
        model_id: str | None = None,
        *,
        quality_weight: float = 1.0,
        speed_weight: float = 1.0,
        cost_weight: float = 1.0,
    ) -> ModelSelection:
        candidates: list[ModelSelection] = []
        providers = [self.get(provider_id)] if provider_id else self.all()
        for provider in providers:
            if provider is None or not provider.enabled:
                continue
            for model in provider.models:
                if model_id and model.id != model_id:
                    continue
                if not model.supports(capability):
                    continue
                score = (
                    model.quality * quality_weight
                    + model.speed * speed_weight
                    - model.cost * cost_weight
                )
                candidates.append(ModelSelection(provider, model, score))
        if not candidates:
            raise ProviderError(
                f"No enabled model supports capability={capability.value!r}"
                + (f" provider={provider_id!r}" if provider_id else "")
                + (f" model={model_id!r}" if model_id else "")
            )
        return max(candidates, key=lambda item: item.score)
