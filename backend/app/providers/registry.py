from __future__ import annotations

from dataclasses import dataclass

from .builtin import MockModelAdapter
from .contracts import ModelAdapter


@dataclass(frozen=True, slots=True)
class RegisteredModel:
    id: str
    provider: str
    adapter: ModelAdapter
    enabled: bool = True
    priority: int = 100


class ModelRegistry:
    """Provider-agnostic model registry with deterministic routing."""

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


def default_provider_registry() -> ModelRegistry:
    """Return a usable zero-cost registry for Mock Mode and local development."""
    registry = ModelRegistry()
    registry.register(RegisteredModel(
        id="mock-deterministic",
        provider="mock",
        adapter=MockModelAdapter(),
        priority=10,
    ))
    return registry
