from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

from .runtime import OrchestratorRuntime


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WorkerLoopConfig:
    poll_interval_seconds: float = 0.5
    recovery_interval_seconds: float = 10.0
    error_backoff_seconds: float = 1.0


class WorkerLoop:
    """Long-running local scheduler/worker loop.

    The loop is intentionally broker-independent: SQLite remains the durable
    queue, while this process continuously claims and executes jobs. Worker
    selection defaults to the runtime registry so specialized jobs cannot be
    accidentally executed by the development mock worker.
    """

    def __init__(
        self,
        runtime: OrchestratorRuntime,
        worker_id: str = "auto",
        config: WorkerLoopConfig | None = None,
    ) -> None:
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        self.runtime = runtime
        self.worker_id = worker_id
        self.config = config or WorkerLoopConfig()
        if (
            self.config.poll_interval_seconds <= 0
            or self.config.recovery_interval_seconds <= 0
            or self.config.error_backoff_seconds <= 0
        ):
            raise ValueError("loop intervals must be positive")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_error: str | None = None
        self._iterations = 0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def last_error(self) -> str | None:
        return self._last_error

    @property
    def iterations(self) -> int:
        return self._iterations

    def start(self) -> None:
        thread = self._thread
        if thread is not None and thread.is_alive():
            return
        if thread is not None and not thread.is_alive():
            self._thread = None
        self._stop.clear()
        self._thread = threading.Thread(target=self.run_forever, name=f"aicf-worker-{self.worker_id}", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is None:
            return
        if thread.is_alive():
            thread.join(timeout=max(0.0, timeout))
        if thread.is_alive():
            # Keep the live thread reference so start() cannot create a second
            # scheduler while the original one is still unwinding.
            logger.warning("Worker loop did not stop within timeout", extra={"worker_id": self.worker_id})
            return
        self._thread = None

    def run_forever(self) -> None:
        last_recovery = 0.0
        while not self._stop.is_set():
            try:
                now = time.monotonic()
                if now - last_recovery >= self.config.recovery_interval_seconds:
                    self.runtime.recover_expired()
                    last_recovery = now

                result = self.runtime.execute_next(self.worker_id)
                self._iterations += 1
                self._last_error = None
                if result is None:
                    self._stop.wait(self.config.poll_interval_seconds)
            except Exception as exc:  # noqa: BLE001 - the loop must survive one bad job
                self._last_error = f"{type(exc).__name__}: {exc}"
                logger.exception("Worker loop iteration failed", extra={"worker_id": self.worker_id})
                self._stop.wait(self.config.error_backoff_seconds)

    def run_once(self) -> bool:
        """Recover leases and execute at most one queued job."""
        try:
            self.runtime.recover_expired()
            result = self.runtime.execute_next(self.worker_id)
            self._iterations += 1
            self._last_error = None
            return result is not None
        except Exception as exc:  # noqa: BLE001 - preserve one-shot caller control
            self._last_error = f"{type(exc).__name__}: {exc}"
            raise
