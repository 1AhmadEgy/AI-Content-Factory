from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..domain.translation import TranslationRequest, TranslationResult


class SQLiteTranslationRepository:
    """Append-only translation history backed by the shared SQLite store."""

    def __init__(self, store: Any) -> None:
        self.store = store
        with self.store._lock, self.store.connection:
            self.store.connection.execute("CREATE TABLE IF NOT EXISTS translations (id TEXT PRIMARY KEY, source_language TEXT NOT NULL, target_language TEXT NOT NULL, source_text TEXT NOT NULL, translated_text TEXT NOT NULL, content_type TEXT NOT NULL, source_id TEXT, provider TEXT NOT NULL, model TEXT, glossary_version INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1, manual INTEGER NOT NULL DEFAULT 0, source_fingerprint TEXT NOT NULL, created_at TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}')")
            self.store.connection.execute("CREATE INDEX IF NOT EXISTS idx_translations_source ON translations(source_id, target_language, version)")
            self.store.connection.execute("CREATE INDEX IF NOT EXISTS idx_translations_fingerprint ON translations(source_fingerprint)")

    def save(self, result: TranslationResult, request: TranslationRequest) -> TranslationResult:
        with self.store._lock, self.store.connection:
            self.store.connection.execute("INSERT INTO translations(id,source_language,target_language,source_text,translated_text,content_type,source_id,provider,model,glossary_version,version,manual,source_fingerprint,created_at,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (result.id, result.source_language, result.target_language, result.source_text, result.translated_text, result.content_type, result.source_id, result.provider, result.model, result.glossary_version, result.version, 1 if result.manual else 0, request.idempotency_key(), result.created_at, json.dumps(result.metadata, ensure_ascii=False, separators=(",", ":"))))
        return result

    def latest(self, request: TranslationRequest) -> TranslationResult | None:
        with self.store._lock:
            row = self.store.connection.execute("SELECT * FROM translations WHERE source_fingerprint=? ORDER BY version DESC, created_at DESC LIMIT 1", (request.idempotency_key(),)).fetchone()
        return self._from_row(row) if row else None

    def get(self, translation_id: str) -> TranslationResult | None:
        with self.store._lock:
            row = self.store.connection.execute("SELECT * FROM translations WHERE id=?", (translation_id,)).fetchone()
        return self._from_row(row) if row else None

    def list(self, *, source_id: str | None = None, target_language: str | None = None, limit: int = 100) -> list[TranslationResult]:
        limit = max(1, min(limit, 500))
        clauses: list[str] = []
        params: list[Any] = []
        if source_id:
            clauses.append("source_id=?")
            params.append(source_id)
        if target_language:
            clauses.append("target_language=?")
            params.append(target_language)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.store._lock:
            rows = self.store.connection.execute(f"SELECT * FROM translations{where} ORDER BY created_at DESC, id DESC LIMIT ?", (*params, limit)).fetchall()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row: sqlite3.Row) -> TranslationResult:
        return TranslationResult(id=row["id"], source_language=row["source_language"], target_language=row["target_language"], source_text=row["source_text"], translated_text=row["translated_text"], content_type=row["content_type"], source_id=row["source_id"], provider=row["provider"], model=row["model"], glossary_version=row["glossary_version"], version=row["version"], manual=bool(row["manual"]), created_at=row["created_at"], metadata=json.loads(row["metadata_json"] or "{}"))
