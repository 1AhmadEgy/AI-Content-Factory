from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ModelCapability:
    category: str
    capabilities: frozenset[str] = field(default_factory=frozenset)
    runtime: str = "CUSTOM"
    license_status: str = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    model: str
    parameters: dict[str, Any] = field(default_factory=dict)
    seed: int | None = None


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    success: bool
    output_asset_ids: list[str] = field(default_factory=list)
    provider_run_id: str | None = None
    metrics: dict[str, float] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


class ModelAdapter(ABC):
    @abstractmethod
    def capability(self) -> ModelCapability: ...

    @abstractmethod
    def health_check(self) -> bool: ...

    @abstractmethod
    def execute(self, request: ProviderRequest) -> ProviderResponse: ...

    @abstractmethod
    def cancel(self, provider_run_id: str) -> bool: ...
