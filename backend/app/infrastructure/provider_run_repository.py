from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..domain.provider_runs import ProviderRun
from .sqlite import SQLiteStore


class SQLiteProviderRunRepository:
    """Durable provider-attempt ledger for local deployments."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        with store._lock, store.connection:
            store.connection.execute("""CREATE TABLE IF NOT EXISTS provider_runs (
                id TEXT PRIMARY KEY, job_id TEXT NOT NULL, provider TEXT NOT NULL,
                model TEXT, request_metadata_json TEXT NOT NULL, response_metadata_json TEXT NOT NULL,
                status TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT,
                duration_ms INTEGER, error_code TEXT, created_at TEXT NOT NULL
            )""")
            store.connection.execute("CREATE INDEX IF NOT EXISTS idx_provider_runs_job ON provider_runs(job_id, created_at)")

    def create(self, run: ProviderRun) -> None:
        with self.store._lock, self.store.connection:
            self.store.connection.execute(
                "INSERT INTO provider_runs VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (run.id, run.job_id, run.provider, run.model,
                 json.dumps(run.request_metadata, ensure_ascii=False, sort_keys=True),
                 json.dumps(run.response_metadata, ensure_ascii=False, sort_keys=True),
                 run.status, run.started_at.isoformat(),
                 run.completed_at.isoformat() if run.completed_at else None,
                 run.duration_ms, run.error_code, run.created_at.isoformat()),
            )

    def complete(self, run_id: str, *, status: str, response_metadata: dict[str, Any] | None = None,
                 error_code: str | None = None) -> ProviderRun:
        row = self.store.connection.execute("SELECT * FROM provider_runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError("PROVIDER_RUN_NOT_FOUND")
        completed = datetime.now(timezone.utc)
        started = datetime.fromisoformat(row["started_at"])
        duration = max(0, int((completed - started).total_seconds() * 1000))
        merged = json.loads(row["response_metadata_json"])
        if response_metadata:
            merged.update(response_metadata)
        with self.store._lock, self.store.connection:
            self.store.connection.execute(
                "UPDATE provider_runs SET response_metadata_json=?,status=?,completed_at=?,duration_ms=?,error_code=? WHERE id=?",
                (json.dumps(merged, ensure_ascii=False, sort_keys=True), status, completed.isoformat(), duration, error_code, run_id),
            )
        return self.get(run_id)

    def get(self, run_id: str) -> ProviderRun:
        row = self.store.connection.execute("SELECT * FROM provider_runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError("PROVIDER_RUN_NOT_FOUND")
        return ProviderRun(
            id=row["id"], job_id=row["job_id"], provider=row["provider"], model=row["model"],
            request_metadata=json.loads(row["request_metadata_json"]), response_metadata=json.loads(row["response_metadata_json"]),
            status=row["status"], started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            duration_ms=row["duration_ms"], error_code=row["error_code"], created_at=datetime.fromisoformat(row["created_at"]),
        )

    def list_for_job(self, job_id: str, limit: int = 50) -> list[ProviderRun]:
        rows = self.store.connection.execute(
            "SELECT id FROM provider_runs WHERE job_id=? ORDER BY created_at DESC,id DESC LIMIT ?", (job_id, limit)
        ).fetchall()
        return [self.get(row["id"]) for row in rows]
