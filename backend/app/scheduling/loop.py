from __future__ import annotations

import threading
import time

from .persistent import PersistentScheduler


class SchedulerLoop:
    def __init__(self, scheduler: PersistentScheduler, interval_seconds: float = 5.0):
        self.scheduler=scheduler; self.interval_seconds=max(0.5,interval_seconds)
        self._stop=threading.Event(); self._thread: threading.Thread | None=None; self.last_error: str | None=None; self.ticks=0

    @property
    def running(self): return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running: return
        self._stop.clear(); self._thread=threading.Thread(target=self._run,name="aicf-scheduler",daemon=True); self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread: self._thread.join(timeout=2)
        self._thread=None

    def _run(self):
        while not self._stop.is_set():
            try: self.scheduler.tick(); self.last_error=None
            except Exception as exc: self.last_error=str(exc)
            self.ticks+=1; self._stop.wait(self.interval_seconds)
