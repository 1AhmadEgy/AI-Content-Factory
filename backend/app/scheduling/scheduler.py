from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable


class JobState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class ScheduledJob:
    id: str
    operation: str
    run_at: str
    payload: dict
    state: JobState = JobState.PENDING
    attempts: int = 0
    max_attempts: int = 3
    lease_owner: str | None = None
    error: str | None = None


class BatchScheduler:
    """Small durable JSON scheduler for development; production can replace storage/clock without changing job contracts."""

    def __init__(self, state_file: str = "data/scheduler.json"):
        self.path = Path(state_file)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.jobs: dict[str, ScheduledJob] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for item in raw:
            self.jobs[item["id"]] = ScheduledJob(**{**item, "state": JobState(item["state"])})

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([asdict(j) for j in self.jobs.values()], ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def enqueue(self, operation: str, payload: dict, run_at: str | None = None, max_attempts: int = 3) -> ScheduledJob:
        job = ScheduledJob(str(uuid.uuid4()), operation, run_at or datetime.now(timezone.utc).isoformat(), payload, max_attempts=max_attempts)
        with self._lock:
            self.jobs[job.id] = job
            self._save()
        return job

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self.jobs.get(job_id)
            if not job or job.state in {JobState.COMPLETED, JobState.CANCELLED}:
                return False
            job.state = JobState.CANCELLED
            job.lease_owner = None
            self._save()
            return True

    def recover(self) -> list[str]:
        recovered: list[str] = []
        with self._lock:
            for job in self.jobs.values():
                if job.state == JobState.RUNNING:
                    job.state = JobState.PENDING
                    job.lease_owner = None
                    recovered.append(job.id)
            self._save()
        return recovered

    def run_due(self, handler: Callable[[ScheduledJob], None], now: datetime | None = None) -> list[str]:
        now = now or datetime.now(timezone.utc)
        completed: list[str] = []
        for job in list(self.jobs.values()):
            if job.state != JobState.PENDING or datetime.fromisoformat(job.run_at.replace("Z", "+00:00")) > now:
                continue
            with self._lock:
                if job.state != JobState.PENDING:
                    continue
                job.state = JobState.RUNNING
                job.lease_owner = str(uuid.uuid4())
                job.attempts += 1
                self._save()
            try:
                handler(job)
                job.state = JobState.COMPLETED
                completed.append(job.id)
            except Exception as exc:
                job.error = str(exc)
                job.state = JobState.PENDING if job.attempts < job.max_attempts else JobState.FAILED
            finally:
                job.lease_owner = None
                with self._lock:
                    self._save()
        return completed
