from __future__ import annotations

from dataclasses import dataclass, field

from ..orchestrator.queue import Worker


@dataclass(frozen=True, slots=True)
class WorkerDescriptor:
    worker: Worker
    capabilities: frozenset[str] = field(default_factory=frozenset)

    @property
    def worker_id(self) -> str:
        return self.worker.worker_type


class WorkerRegistry:
    """Capability-based registry over the canonical orchestrator Worker contract."""

    def __init__(self) -> None:
        self._workers: dict[str, WorkerDescriptor] = {}

    def register(self, worker: Worker, capabilities: set[str] | frozenset[str] | None = None) -> None:
        worker_id = worker.worker_type
        if worker_id in self._workers:
            raise ValueError(f"Worker already registered: {worker_id}")
        self._workers[worker_id] = WorkerDescriptor(worker, frozenset(capabilities or set()))

    def get(self, worker_id: str) -> Worker:
        return self._workers[worker_id].worker

    def find(self, capability: str) -> list[Worker]:
        return [
            item.worker for item in self._workers.values()
            if capability in item.capabilities and item.worker.health_check()
        ]

    def names(self) -> list[str]:
        return sorted(self._workers)
