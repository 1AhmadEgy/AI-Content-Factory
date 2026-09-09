from __future__ import annotations

from dataclasses import dataclass, field

from .contracts import Worker


@dataclass(frozen=True, slots=True)
class WorkerDescriptor:
    worker: Worker
    capabilities: frozenset[str] = field(default_factory=frozenset)


class WorkerRegistry:
    def __init__(self) -> None:
        self._workers: dict[str, WorkerDescriptor] = {}

    def register(self, worker: Worker, capabilities: set[str] | frozenset[str] | None = None) -> None:
        if worker.name in self._workers:
            raise ValueError(f"Worker already registered: {worker.name}")
        self._workers[worker.name] = WorkerDescriptor(worker, frozenset(capabilities or set()))

    def get(self, name: str) -> Worker:
        return self._workers[name].worker

    def find(self, capability: str) -> list[Worker]:
        return [item.worker for item in self._workers.values() if capability in item.capabilities and item.worker.health_check()]

    def names(self) -> list[str]:
        return sorted(self._workers)
