from __future__ import annotations

from threading import Event, Lock


class CancellationRegistry:
    """Thread-safe cooperative cancellation registry keyed by job id."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._events: dict[str, Event] = {}

    def token(self, job_id: str) -> Event:
        with self._lock:
            return self._events.setdefault(job_id, Event())

    def cancel(self, job_id: str) -> None:
        self.token(job_id).set()

    def is_cancelled(self, job_id: str) -> bool:
        return self.token(job_id).is_set()

    def clear(self, job_id: str) -> None:
        with self._lock:
            self._events.pop(job_id, None)
