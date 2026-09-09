from __future__ import annotations

from dataclasses import dataclass

from .job_executor import JobExecutor
from .queue import JobQueue


@dataclass(slots=True)
class SchedulerStats:
    claimed: int = 0
    completed: int = 0
    failed: int = 0


class JobScheduler:
    """Small deterministic scheduler; production deployment can run one instance per worker pool."""

    def __init__(self, queue: JobQueue, executor: JobExecutor) -> None:
        self.queue = queue
        self.executor = executor
        self.running = False

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def tick(self, limit: int = 1) -> SchedulerStats:
        stats = SchedulerStats()
        if not self.running:
            return stats
        for _ in range(max(0, limit)):
            job = self.queue.claim_next()
            if job is None:
                break
            stats.claimed += 1
            result = self.executor.execute(job)
            if result.success:
                stats.completed += 1
            else:
                stats.failed += 1
        return stats
