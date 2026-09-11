from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..infrastructure.sqlite import SQLiteStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectContextStore:
    """Durable, append-only project/series memory with a current materialized snapshot."""

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.store._lock, self.store.connection:
            self.store.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS project_contexts (
                    project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL DEFAULT 0,
                    context_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS project_context_events (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    version INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id TEXT,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_project_context_events_project
                    ON project_context_events(project_id, version DESC);
                """
            )

    def get(self, project_id: str) -> dict[str, Any]:
        with self.store._lock:
            row = self.store.connection.execute(
                "SELECT version, context_json, created_at, updated_at FROM project_contexts WHERE project_id=?",
                (project_id,),
            ).fetchone()
        if row is None:
            return {"projectId": project_id, "version": 0, "context": {}, "createdAt": None, "updatedAt": None}
        return {"projectId": project_id, "version": row["version"], "context": json.loads(row["context_json"] or "{}"), "createdAt": row["created_at"], "updatedAt": row["updated_at"]}

    def save(self, project_id: str, context: dict[str, Any], *, event_type: str = "context.updated", entity_type: str | None = None, entity_id: str | None = None, event_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        now = _now()
        payload = event_payload if event_payload is not None else context
        with self.store._lock, self.store.connection:
            row = self.store.connection.execute("SELECT version, created_at FROM project_contexts WHERE project_id=?", (project_id,)).fetchone()
            version = int(row["version"]) + 1 if row else 1
            created_at = row["created_at"] if row else now
            self.store.connection.execute(
                "INSERT INTO project_contexts(project_id,version,context_json,created_at,updated_at) VALUES(?,?,?,?,?) "
                "ON CONFLICT(project_id) DO UPDATE SET version=excluded.version, context_json=excluded.context_json, updated_at=excluded.updated_at",
                (project_id, version, json.dumps(context, ensure_ascii=False, separators=(",", ":")), created_at, now),
            )
            self.store.connection.execute(
                "INSERT INTO project_context_events(id,project_id,version,event_type,entity_type,entity_id,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (f"ctxevt_{uuid4().hex}", project_id, version, event_type, entity_type, entity_id, json.dumps(payload, ensure_ascii=False, separators=(",", ":")), now),
            )
        return self.get(project_id)

    def merge(self, project_id: str, patch: dict[str, Any], *, event_type: str = "context.merged", entity_type: str | None = None, entity_id: str | None = None) -> dict[str, Any]:
        current = self.get(project_id)["context"]
        merged = dict(current)
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                nested = dict(merged[key]); nested.update(value); merged[key] = nested
            else:
                merged[key] = value
        return self.save(project_id, merged, event_type=event_type, entity_type=entity_type, entity_id=entity_id, event_payload=patch)

    def append_event(self, project_id: str, event_type: str, payload: dict[str, Any], *, entity_type: str | None = None, entity_id: str | None = None) -> dict[str, Any]:
        current = self.get(project_id)
        return self.save(project_id, current["context"], event_type=event_type, entity_type=entity_type, entity_id=entity_id, event_payload=payload)

    def events(self, project_id: str, limit: int = 100) -> list[dict[str, Any]]:
        with self.store._lock:
            rows = self.store.connection.execute("SELECT id, version, event_type, entity_type, entity_id, payload_json, created_at FROM project_context_events WHERE project_id=? ORDER BY version DESC LIMIT ?", (project_id, max(1, min(limit, 1000)))).fetchall()
        return [{"id": r["id"], "version": r["version"], "eventType": r["event_type"], "entityType": r["entity_type"], "entityId": r["entity_id"], "payload": json.loads(r["payload_json"] or "{}"), "createdAt": r["created_at"]} for r in rows]
