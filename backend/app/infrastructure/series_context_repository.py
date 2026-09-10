from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .sqlite import SQLiteStore


class SQLiteSeriesContextRepository:
    """Durable series memory with append-only episode snapshots."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        with store._lock, store.connection:
            store.connection.execute("CREATE TABLE IF NOT EXISTS series_contexts (project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE, context_json TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
            store.connection.execute("CREATE TABLE IF NOT EXISTS series_context_snapshots (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, episode_number INTEGER NOT NULL, episode_id TEXT, context_json TEXT NOT NULL, created_at TEXT NOT NULL)")
            store.connection.execute("CREATE INDEX IF NOT EXISTS idx_series_snapshots_project_episode ON series_context_snapshots(project_id, episode_number)")

    def get(self, project_id: str) -> dict[str, Any] | None:
        row = self.store._get("series_contexts", project_id)
        return None if row is None else json.loads(row["context_json"])

    def save(self, project_id: str, context: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(context, ensure_ascii=False, sort_keys=True)
        with self.store._lock, self.store.connection:
            row = self.store._get("series_contexts", project_id)
            version = (int(row["version"]) + 1) if row else 1
            if row:
                self.store.connection.execute("UPDATE series_contexts SET context_json=?,version=?,updated_at=? WHERE project_id=?", (payload, version, now, project_id))
            else:
                self.store.connection.execute("INSERT INTO series_contexts(project_id,context_json,version,created_at,updated_at) VALUES(?,?,?,?,?)", (project_id, payload, version, now, now))
        return context

    def snapshot(self, project_id: str, episode_number: int, context: dict[str, Any], episode_id: str | None = None) -> dict[str, Any]:
        import uuid
        now = datetime.now(timezone.utc).isoformat()
        snapshot = json.loads(json.dumps(context, ensure_ascii=False))
        payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
        with self.store._lock, self.store.connection:
            self.store.connection.execute("INSERT INTO series_context_snapshots(id,project_id,episode_number,episode_id,context_json,created_at) VALUES(?,?,?,?,?,?)", (f"series_snap_{uuid.uuid4().hex}", project_id, episode_number, episode_id, payload, now))
        return snapshot

    def list_snapshots(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        with self.store._lock:
            rows = self.store.connection.execute("SELECT id,episode_number,episode_id,context_json,created_at FROM series_context_snapshots WHERE project_id=? ORDER BY episode_number DESC,id DESC LIMIT ?", (project_id, limit)).fetchall()
        return [{"id": r["id"], "episodeNumber": r["episode_number"], "episodeId": r["episode_id"], "context": json.loads(r["context_json"]), "createdAt": r["created_at"]} for r in rows]
