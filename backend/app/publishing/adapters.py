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
    payload: Mapping[str, Any] | None = None


class PublishingAdapter(ABC):
    name: str

    @abstractmethod
    def validate(self, request: PublishRequest) -> list[str]: ...

    @abstractmethod
    def publish(self, request: PublishRequest) -> PublishResult: ...

    def schedule(self, request: PublishRequest) -> PublishResult:
        return self.publish(request)


class DryRunAdapter(PublishingAdapter):
    name = "dry-run"

    def validate(self, request: PublishRequest) -> list[str]:
        return [] if request.asset_path else ["ASSET_PATH_REQUIRED"]

    def publish(self, request: PublishRequest) -> PublishResult:
        errors = self.validate(request)
        if errors:
            return PublishResult(self.name, "FAILED", error=";".join(errors))
        return PublishResult(self.name, "DRY_RUN", external_id=f"dry:{request.title}", payload={"scheduledAt": request.scheduled_at})


class _PlatformAdapter(PublishingAdapter):
    platform: str

    @property
    def name(self) -> str:
        return self.platform

    def validate(self, request: PublishRequest) -> list[str]:
        errors: list[str] = []
        if not request.asset_path:
            errors.append("ASSET_PATH_REQUIRED")
        if not request.title.strip():
            errors.append("TITLE_REQUIRED")
        return errors

    def publish(self, request: PublishRequest) -> PublishResult:
        errors = self.validate(request)
        if errors:
            return PublishResult(self.name, "FAILED", error=";".join(errors))
        return PublishResult(self.name, "READY", external_id=None, payload={"assetPath": request.asset_path, "title": request.title, "description": request.description, "scheduledAt": request.scheduled_at, "metadata": dict(request.metadata or {})})


class YouTubeAdapter(_PlatformAdapter):
    platform = "youtube"


class TikTokAdapter(_PlatformAdapter):
    platform = "tiktok"


class InstagramAdapter(_PlatformAdapter):
    platform = "instagram"


class FacebookAdapter(_PlatformAdapter):
    platform = "facebook"


class AdapterRegistry:
    def __init__(self, adapters: list[PublishingAdapter] | None = None):
        defaults = [DryRunAdapter(), YouTubeAdapter(), TikTokAdapter(), InstagramAdapter(), FacebookAdapter()]
        self._adapters = {a.name: a for a in (adapters or defaults)}

    def register(self, adapter: PublishingAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> PublishingAdapter:
        if name not in self._adapters:
            raise KeyError(f"PUBLISH_ADAPTER_NOT_FOUND:{name}")
        return self._adapters[name]

    def names(self) -> list[str]:
        return sorted(self._adapters)
