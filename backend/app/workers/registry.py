from __future__ import annotations

from dataclasses import dataclass, field

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

    def names(self) -> list[str]:
        return sorted(self._workers)
