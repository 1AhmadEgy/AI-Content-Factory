from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from .runtime import OrchestratorRuntime


@dataclass(frozen=True, slots=True)
class WorkerLoopConfig:
    poll_interval_seconds: float = 0.5
    recovery_interval_seconds: float = 10.0


class WorkerLoop:
    """Long-running local scheduler/worker loop.

    The loop is intentionally broker-independent: SQLite remains the durable
    queue, while this process continuously claims and executes jobs. A later
    Redis-backed implementation can reuse the same runtime contract.
    """

    def __init__(
        self,
        runtime: OrchestratorRuntime,
        worker_id: str = "mock",
        config: WorkerLoopConfig | None = None,
    ) -> None:
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        self.runtime = runtime
        self.worker_id = worker_id
        self.config = config or WorkerLoopConfig()
        if self.config.poll_interval_seconds <= 0 or self.config.recovery_interval_seconds <= 0:
            raise ValueError("loop intervals must be positive")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self.run_forever, name=f"aicf-worker-{self.worker_id}", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(0.0, timeout))
        self._thread = None

    def run_forever(self) -> None:
        last_recovery = 0.0
        while not self._stop.is_set():
            now = time.monotonic()
            if now - last_recovery >= self.config.recovery_interval_seconds:
                self.runtime.recover_expired()
                last_recovery = now

            result = self.runtime.execute_next(self.worker_id)
            if result is None:
                self._stop.wait(self.config.poll_interval_seconds)

    def run_once(self) -> bool:
        """Recover leases and execute at most one queued job."""
        self.runtime.recover_expired()
        return self.runtime.execute_next(self.worker_id) is not None
