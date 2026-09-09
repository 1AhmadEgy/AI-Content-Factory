from __future__ import annotations

import threading


class LeaseHeartbeat:
    """Runs periodic queue heartbeats while a cooperative job is executing."""

    def __init__(self, queue, job_id: str, worker_id: str, interval_seconds: float = 5.0) -> None:
        self.queue = queue
        self.job_id = job_id
        self.worker_id = worker_id
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"heartbeat-{self.job_id}")
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.queue.heartbeat(self.job_id, self.worker_id)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=max(1.0, self.interval_seconds * 2))
