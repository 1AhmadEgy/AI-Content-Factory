from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelRoute:
    provider: str
    model: str
    priority: int = 100


class ModelRouter:
    def __init__(self, routes: list[ModelRoute] | None = None) -> None:
        self._routes = sorted(routes or [], key=lambda item: item.priority)

    def add(self, route: ModelRoute) -> None:
        self._routes.append(route)
        self._routes.sort(key=lambda item: item.priority)

    def select(self, requested_provider: str | None = None, requested_model: str | None = None) -> ModelRoute:
        candidates = self._routes
        if requested_provider:
            candidates = [r for r in candidates if r.provider == requested_provider]
        if requested_model:
            candidates = [r for r in candidates if r.model == requested_model]
        if not candidates:
            raise LookupError("No model route matches the requested provider/model.")
        return min(candidates, key=lambda item: item.priority)
