from __future__ import annotations

import json
from ..domain.job_events import JobEvent
from .sqlite import SQLiteStore, _dt, _parse_dt, _json


class SQLiteJobEventRepository:
    """Append-only durable event log for job lifecycle/progress events."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        with store._lock, store.connection:
            store.connection.execute(
                """CREATE TABLE IF NOT EXISTS job_events (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )"""
            )
            store.connection.execute("CREATE INDEX IF NOT EXISTS idx_job_events_job_created ON job_events(job_id, created_at, id)")

    def append(self, event: JobEvent) -> JobEvent:
        self.store._insert(
            "INSERT INTO job_events(id,job_id,project_id,event_type,status,progress,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (event.id, event.job_id, event.project_id, event.event_type, event.status, event.progress, _json(event.payload), _dt(event.created_at)),
        )
        return event

    def list_for_job(self, job_id: str, limit: int = 200) -> list[JobEvent]:
        with self.store._lock:
            rows = self.store.connection.execute(
                "SELECT * FROM job_events WHERE job_id=? ORDER BY created_at ASC, id ASC LIMIT ?",
                (job_id, max(1, min(limit, 1000))),
            ).fetchall()
        return [
            JobEvent(
                id=row["id"], job_id=row["job_id"], project_id=row["project_id"],
                event_type=row["event_type"], status=row["status"], progress=row["progress"],
                payload=json.loads(row["payload_json"]), created_at=_parse_dt(row["created_at"]),
            ) for row in rows
        ]
