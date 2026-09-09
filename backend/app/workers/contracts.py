from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class WorkerContext:
    worker_id: str
    project_id: str
    job_id: str
    attempt: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WorkerResult:
    success: bool
    asset_ids: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    provider_run_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class Worker(ABC):
    name: str = "worker"

    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def health_check(self) -> bool: ...

    @abstractmethod
    def execute(self, context: WorkerContext, parameters: dict[str, Any]) -> WorkerResult: ...

    @abstractmethod
    def cancel(self, job_id: str) -> bool: ...

    @abstractmethod
    def shutdown(self) -> None: ...
