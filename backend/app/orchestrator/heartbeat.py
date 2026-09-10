from __future__ import annotations

import logging
import threading

from .queue import JobLease


logger = logging.getLogger(__name__)


class LeaseHeartbeat:
    """Renews one queue lease until execution completes or the heartbeat stops."""

    def __init__(self, queue, lease: JobLease, interval_seconds: float = 5.0) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.queue = queue
        self.lease = lease
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        thread = self._thread
        if thread is not None and thread.is_alive():
            return
        if thread is not None and not thread.is_alive():
            self._thread = None
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name=f"heartbeat-{self.lease.job_id}",
        )
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                self.queue.heartbeat(self.lease)
            except Exception:  # noqa: BLE001 - lease loss is handled by the executor
                logger.exception(
                    "Lease heartbeat failed",
                    extra={"job_id": self.lease.job_id, "worker_id": self.lease.worker_id},
                )

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is None:
            return
        if thread.is_alive():
            thread.join(timeout=max(1.0, self.interval_seconds * 2))
        if thread.is_alive():
            # Do not clear the live reference: callers must not accidentally
            # start a second heartbeat for the same lease.
            logger.warning(
                "Lease heartbeat did not stop within timeout",
                extra={"job_id": self.lease.job_id, "worker_id": self.lease.worker_id},
            )
            return
        self._thread = None
