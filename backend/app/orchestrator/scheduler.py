from __future__ import annotations

from dataclasses import dataclass

from .job_executor import JobExecutor
from .queue import JobQueue


@dataclass(slots=True)
class SchedulerStats:
    claimed: int = 0
    completed: int = 0
    failed: int = 0
    recovered: int = 0


class JobScheduler:
    """Deterministic lease-aware scheduler for a single worker identity."""

    def __init__(self, queue: JobQueue, executor: JobExecutor, worker_id: str) -> None:
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        self.queue = queue
        self.executor = executor
        self.worker_id = worker_id
        self.running = False
        self._initialized = False

    def start(self) -> None:
        if self.running:
            return
        worker = self.executor.workers.get(self.worker_id)
        worker.initialize()
        self._initialized = True
        self.running = True

    def stop(self) -> None:
        if not self.running:
            return
        try:
            if self._initialized:
                self.executor.workers.get(self.worker_id).shutdown()
        finally:
            self._initialized = False
            self.running = False

    def tick(self, limit: int = 1) -> SchedulerStats:
        stats = SchedulerStats()
        if not self.running:
            return stats
        stats.recovered = self.queue.release_expired()
        for _ in range(max(0, limit)):
            claimed = self.queue.claim_next(self.worker_id)
            if claimed is None:
                break
            job, lease = claimed
            stats.claimed += 1
            result = self.executor.execute_claimed(job, lease, worker_id=self.worker_id)
            if result.status.value == "COMPLETED":
                stats.completed += 1
            elif result.status.value == "FAILED":
                stats.failed += 1
        return stats
