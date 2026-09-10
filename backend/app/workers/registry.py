from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.jobs import JobType
from ..orchestrator.queue import Worker


@dataclass(frozen=True, slots=True)
class WorkerDescriptor:
    worker: Worker
    capabilities: frozenset[str] = field(default_factory=frozenset)


class WorkerRegistry:
    """Capability-based registry with explicit production routing."""

    def __init__(self) -> None:
        self._workers: dict[str, WorkerDescriptor] = {}

    def register(self, worker: Worker, capabilities: set[str] | frozenset[str] | None = None, worker_id: str | None = None) -> None:
        key = worker_id or getattr(worker, "worker_type", None) or worker.__class__.__name__
        if key in self._workers:
            raise ValueError(f"Worker already registered: {key}")
        self._workers[key] = WorkerDescriptor(worker, frozenset(capabilities or set()))

    def get(self, worker_id: str) -> Worker:
        return self._workers[worker_id].worker

    def find(self, capability: str) -> list[Worker]:
        return [d.worker for d in self._workers.values() if capability in d.capabilities and d.worker.health_check()]

    def resolve_for_job(self, job_type: JobType | str) -> str:
        name = job_type.value if isinstance(job_type, JobType) else str(job_type)
        specialized = {"QC": "quality-control", "BEST_TAKE": "best-take", "TIMELINE": "timeline", "RENDER": "render", "SUBTITLE": "media-document", "THUMBNAIL": "media-document", "METADATA": "media-document", "PUBLISH": "publish"}
        worker_id = specialized.get(name)
        if worker_id:
            if worker_id not in self._workers or not self._workers[worker_id].worker.health_check():
                raise KeyError(f"Required worker unavailable for job type: {name}")
            return worker_id
        if "provider-generation" in self._workers and self._workers["provider-generation"].worker.health_check() and name in self._workers["provider-generation"].capabilities:
            return "provider-generation"
        if "mock" in self._workers and self._workers["mock"].worker.health_check():
            return "mock"
        candidates = self.find(name)
        for worker_id, descriptor in self._workers.items():
            if descriptor.worker in candidates:
                return worker_id
        raise KeyError(f"No healthy worker for job type: {name}")

    def names(self) -> list[str]:
        return sorted(self._workers)
