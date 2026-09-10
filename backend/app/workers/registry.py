from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.jobs import JobType
from ..orchestrator.queue import Worker


@dataclass(frozen=True, slots=True)
class WorkerDescriptor:
    worker: Worker
    capabilities: frozenset[str] = field(default_factory=frozenset)


class WorkerRegistry:
    """Capability-based registry over the canonical orchestrator Worker contract."""

    def __init__(self) -> None:
        self._workers: dict[str, WorkerDescriptor] = {}

    def register(
        self,
        worker: Worker,
        capabilities: set[str] | frozenset[str] | None = None,
        worker_id: str | None = None,
    ) -> None:
        key = worker_id or getattr(worker, "worker_type", None) or worker.__class__.__name__
        if key in self._workers:
            raise ValueError(f"Worker already registered: {key}")
        self._workers[key] = WorkerDescriptor(worker, frozenset(capabilities or set()))

    def get(self, worker_id: str) -> Worker:
        return self._workers[worker_id].worker

    def find(self, capability: str) -> list[Worker]:
        return [
            item.worker for item in self._workers.values()
            if capability in item.capabilities and item.worker.health_check()
        ]

    def resolve_for_job(self, job_type: JobType | str) -> str:
        """Select the healthy specialized worker for a job, with provider fallback."""
        name = job_type.value if isinstance(job_type, JobType) else str(job_type)
        specialized = {
            "QC": "quality-control",
            "BEST_TAKE": "best-take",
            "TIMELINE": "timeline",
            "RENDER": "render",
        }.get(name)
        if specialized and specialized in self._workers and self._workers[specialized].worker.health_check():
            return specialized
        if "provider-generation" in self._workers and self._workers["provider-generation"].worker.health_check():
            descriptor = self._workers["provider-generation"]
            if name in descriptor.capabilities:
                return "provider-generation"
        if "mock" in self._workers and self._workers["mock"].worker.health_check():
            return "mock"
        candidates = self.find(name)
        if candidates:
            for worker_id, descriptor in self._workers.items():
                if descriptor.worker in candidates:
                    return worker_id
        raise KeyError(f"No healthy worker for job type: {name}")

    def names(self) -> list[str]:
        return sorted(self._workers)
