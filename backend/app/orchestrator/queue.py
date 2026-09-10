"""Queue and worker contracts used by the orchestrator.

These interfaces keep scheduling independent from a particular broker. The
initial implementation can use SQLite/local execution; Redis or another
persistent broker can be added later without changing worker code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

from ..domain.jobs import GenerationJob, JobStatus


@dataclass(slots=True, frozen=True)
class JobLease:
    job_id: str
    worker_id: str
    lease_id: str
    expires_at: str


@dataclass(slots=True)
class WorkerContext:
    worker_id: str
    lease_id: str
    cancellation_requested: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    progress_callback: Callable[[float, str], None] | None = None

    def report_progress(self, progress: float, stage: str) -> None:
        if self.progress_callback is not None:
            self.progress_callback(max(0.0, min(1.0, progress)), stage)


@dataclass(slots=True)
class JobExecutionResult:
    success: bool
    asset_ids: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    provider_run_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False


class JobQueue(ABC):
    @abstractmethod
    def enqueue(self, job: GenerationJob) -> None:
        """Make a persisted job eligible for scheduling."""

    @abstractmethod
    def claim_next(self, worker_id: str) -> tuple[GenerationJob, JobLease] | None:
        """Atomically claim the highest-priority runnable job."""

    def claim(self, job_id: str, worker_id: str) -> tuple[GenerationJob, JobLease] | None:
        """Atomically claim one specific runnable job when supported."""
        raise NotImplementedError("TARGETED_CLAIM_NOT_SUPPORTED")

    @abstractmethod
    def heartbeat(self, lease: JobLease) -> None:
        """Extend an active lease."""

    def is_lease_active(self, lease: JobLease) -> bool:
        """Return whether a lease is still owned by its worker."""
        return True

    @abstractmethod
    def acknowledge(self, lease: JobLease, status: JobStatus) -> None:
        """Atomically release the lease and persist the queue-visible status."""

    @abstractmethod
    def release_expired(self) -> int:
        """Return expired leases to the runnable queue and report their count."""


class Worker(ABC):
    """Provider-agnostic worker lifecycle contract."""

    worker_type: str

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass

    @abstractmethod
    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        pass

    @abstractmethod
    def cancel(self, job_id: str) -> None:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass
