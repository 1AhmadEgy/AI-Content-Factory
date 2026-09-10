from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..domain.translation import TranslationRequest, TranslationResult


class SQLiteTranslationRepository:
    """Append-only translation history backed by the shared SQLite store.

    A translation is never updated in place.  A changed source creates a new
    fingerprint; a re-translation of the same source fingerprint gets a new
    translation version.  Manual translations take precedence when resolving
    the current translation for a source fingerprint.
    """

    def __init__(self, store: Any) -> None:
        self.store = store
        with self.store._lock, self.store.connection:
            self.store.connection.execute(
                "CREATE TABLE IF NOT EXISTS translations ("
                "id TEXT PRIMARY KEY, source_language TEXT NOT NULL, target_language TEXT NOT NULL, "
                "source_text TEXT NOT NULL, translated_text TEXT NOT NULL, content_type TEXT NOT NULL, "
                "source_id TEXT, source_version INTEGER NOT NULL DEFAULT 1, provider TEXT NOT NULL, model TEXT, "
                "glossary_version INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1, "
                "manual INTEGER NOT NULL DEFAULT 0, source_fingerprint TEXT NOT NULL, created_at TEXT NOT NULL, "
                "metadata_json TEXT NOT NULL DEFAULT '{}')"
            )
            columns = {
                row["name"]
                for row in self.store.connection.execute("PRAGMA table_info(translations)").fetchall()
            }
            if "source_version" not in columns:
                self.store.connection.execute(
                    "ALTER TABLE translations ADD COLUMN source_version INTEGER NOT NULL DEFAULT 1"
                )
            self.store.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_translations_source ON translations(source_id, target_language, version)"
            )
            self.store.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_translations_fingerprint ON translations(source_fingerprint, version, created_at)"
            )
            self.store.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_translations_current ON translations(source_fingerprint, manual, version, created_at)"
            )

    def save(self, result: TranslationResult, request: TranslationRequest) -> TranslationResult:
        """Persist an immutable result and resolve version collisions safely."""
        with self.store._lock, self.store.connection:
            existing = self.store.connection.execute(
                "SELECT * FROM translations WHERE source_fingerprint=? AND version=? "
                "ORDER BY manual DESC, created_at DESC LIMIT 1",
                (request.idempotency_key(), result.version),
            ).fetchone()

            if existing is not None:
                # Automated retries must reuse an existing manual translation.
                if bool(existing["manual"]):
                    return self._from_row(existing)
                # Never overwrite an existing row. Allocate the next immutable version.
                next_version = int(
                    self.store.connection.execute(
                        "SELECT COALESCE(MAX(version), 0) + 1 FROM translations WHERE source_fingerprint=?",
                        (request.idempotency_key(),),
                    ).fetchone()[0]
                )
                result = TranslationResult(
                    id=result.id,
                    source_language=result.source_language,
                    target_language=result.target_language,
                    source_text=result.source_text,
                    translated_text=result.translated_text,
                    content_type=result.content_type,
                    source_id=result.source_id,
                    provider=result.provider,
                    model=result.model,
                    glossary_version=result.glossary_version,
                    version=next_version,
                    manual=result.manual,
                    created_at=result.created_at,
                    metadata={**result.metadata, "versionAllocated": "repository"},
                )

            self.store.connection.execute(
                "INSERT INTO translations(id,source_language,target_language,source_text,translated_text,content_type,source_id,source_version,provider,model,glossary_version,version,manual,source_fingerprint,created_at,metadata_json) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    result.id,
                    result.source_language,
                    result.target_language,
                    result.source_text,
                    result.translated_text,
                    result.content_type,
                    result.source_id,
                    request.source_version,
                    result.provider,
                    result.model,
                    result.glossary_version,
                    result.version,
                    1 if result.manual else 0,
                    request.idempotency_key(),
                    result.created_at,
                    json.dumps(result.metadata, ensure_ascii=False, separators=(",", ":")),
                ),
            )
        return result

    def latest(self, request: TranslationRequest) -> TranslationResult | None:
        with self.store._lock:
            row = self.store.connection.execute(
                "SELECT * FROM translations WHERE source_fingerprint=? "
                "ORDER BY manual DESC, version DESC, created_at DESC LIMIT 1",
                (request.idempotency_key(),),
            ).fetchone()
        return self._from_row(row) if row else None

    def get(self, translation_id: str) -> TranslationResult | None:
        with self.store._lock:
            row = self.store.connection.execute(
                "SELECT * FROM translations WHERE id=?", (translation_id,)
            ).fetchone()
        return self._from_row(row) if row else None

    def list(
        self,
        *,
        source_id: str | None = None,
        target_language: str | None = None,
        limit: int = 100,
    ) -> list[TranslationResult]:
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
            rows = self.store.connection.execute(
                f"SELECT * FROM translations{where} ORDER BY created_at DESC, id DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row: sqlite3.Row) -> TranslationResult:
        return TranslationResult(
            id=row["id"],
            source_language=row["source_language"],
            target_language=row["target_language"],
            source_text=row["source_text"],
            translated_text=row["translated_text"],
            content_type=row["content_type"],
            source_id=row["source_id"],
            provider=row["provider"],
            model=row["model"],
            glossary_version=row["glossary_version"],
            version=row["version"],
            manual=bool(row["manual"]),
            created_at=row["created_at"],
            metadata=json.loads(row["metadata_json"] or "{}"),
        )
