from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
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


class HttpPublishingAdapter(PublishingAdapter):
    """Real HTTP publishing transport configured per platform.

    The remote endpoint is responsible for the platform-specific API call.
    No local success is reported unless the endpoint returns a successful
    HTTP response containing a real external publication identifier.
    """

    def __init__(self, name: str, endpoint: str, token: str | None = None, timeout_seconds: int = 120) -> None:
        self.name = name
        self.endpoint = endpoint
        self.token = token
        self.timeout_seconds = max(1, timeout_seconds)

    def validate(self, request: PublishRequest) -> list[str]:
        errors: list[str] = []
        if not self.endpoint:
            errors.append("PUBLISH_ENDPOINT_NOT_CONFIGURED")
        if not request.asset_path:
            errors.append("ASSET_PATH_REQUIRED")
        if not os.path.isfile(request.asset_path):
            errors.append("ASSET_FILE_NOT_FOUND")
        if not request.title.strip():
            errors.append("TITLE_REQUIRED")
        return errors

    def publish(self, request: PublishRequest) -> PublishResult:
        errors = self.validate(request)
        if errors:
            return PublishResult(self.name, "FAILED", error=";".join(errors))
        payload = {
            "platform": self.name,
            "assetPath": request.asset_path,
            "title": request.title,
            "description": request.description,
            "scheduledAt": request.scheduled_at,
            "metadata": dict(request.metadata or {}),
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                response_data = json.loads(raw) if raw else {}
                external_id = response_data.get("externalId") or response_data.get("id")
                if not external_id:
                    return PublishResult(self.name, "FAILED", error="PUBLISH_EXTERNAL_ID_MISSING", payload=response_data if isinstance(response_data, dict) else {})
                return PublishResult(self.name, "PUBLISHED", external_id=str(external_id), payload=response_data if isinstance(response_data, dict) else {})
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[-2000:]
            return PublishResult(self.name, "FAILED", error=f"PUBLISH_HTTP_{exc.code}:{detail}")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            return PublishResult(self.name, "FAILED", error=f"PUBLISH_TRANSPORT_ERROR:{exc}", payload={})


class AdapterRegistry:
    def __init__(self, adapters: list[PublishingAdapter] | None = None):
        if adapters is not None:
            self._adapters = {a.name: a for a in adapters}
        else:
            configured: list[PublishingAdapter] = []
            for platform in ("youtube", "tiktok", "instagram", "facebook"):
                endpoint = os.getenv(f"AICF_PUBLISH_{platform.upper()}_ENDPOINT", "").strip()
                token = os.getenv(f"AICF_PUBLISH_{platform.upper()}_TOKEN", "").strip() or None
                if endpoint:
                    configured.append(HttpPublishingAdapter(platform, endpoint, token))
            self._adapters = {a.name: a for a in configured}

    def register(self, adapter: PublishingAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> PublishingAdapter:
        if name not in self._adapters:
            raise KeyError(f"PUBLISH_ADAPTER_NOT_FOUND:{name}")
        return self._adapters[name]

    def names(self) -> list[str]:
        return sorted(self._adapters)
