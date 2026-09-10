from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class PublishRequest:
    asset_path: str
    title: str
    description: str = ""
    scheduled_at: str | None = None
    metadata: Mapping[str, str] | None = None


@dataclass(frozen=True, slots=True)
class PublishResult:
    provider: str
    status: str
    external_id: str | None = None
    error: str | None = None


class PublishingAdapter(ABC):
    name: str

    @abstractmethod
    def validate(self, request: PublishRequest) -> list[str]: ...

    @abstractmethod
    def publish(self, request: PublishRequest) -> PublishResult: ...

    def schedule(self, request: PublishRequest) -> PublishResult:
        return self.publish(request)


class DryRunAdapter(PublishingAdapter):
    """Safe default adapter. Real providers can implement the same contract without touching orchestration."""
    name = "dry-run"

    def validate(self, request: PublishRequest) -> list[str]:
        return [] if request.asset_path else ["ASSET_PATH_REQUIRED"]

    def publish(self, request: PublishRequest) -> PublishResult:
        errors = self.validate(request)
        if errors:
            return PublishResult(self.name, "FAILED", error=";".join(errors))
        return PublishResult(self.name, "DRY_RUN", external_id=f"dry:{request.title}")


class AdapterRegistry:
    def __init__(self, adapters: list[PublishingAdapter] | None = None):
        self._adapters = {a.name: a for a in (adapters or [DryRunAdapter()])}

    def register(self, adapter: PublishingAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> PublishingAdapter:
        if name not in self._adapters:
            raise KeyError(f"PUBLISH_ADAPTER_NOT_FOUND:{name}")
        return self._adapters[name]

    def names(self) -> list[str]:
        return sorted(self._adapters)
