from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .sqlite import SQLiteStore


@dataclass(frozen=True, slots=True)
class ProviderCacheEntry:
    cache_key: str
    provider: str
    model: str
    output_text: str | None
    output_bytes: bytes | None
    output_mime_type: str | None
    output_filename: str | None
    output_metadata: dict[str, Any]
    metrics: dict[str, float]


class SQLiteProviderCache:
    """Durable success-only provider response cache with stampede protection."""

    def __init__(self, store: SQLiteStore, ttl_seconds: int = 86400, max_bytes: int = 20 * 1024 * 1024) -> None:
        if ttl_seconds <= 0 or max_bytes <= 0:
            raise ValueError("cache limits must be positive")
        self.store = store
        self.ttl_seconds = ttl_seconds
        self.max_bytes = max_bytes
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.store._lock, self.store.connection:
            self.store.connection.executescript("""
                CREATE TABLE IF NOT EXISTS provider_cache (
                    cache_key TEXT PRIMARY KEY, provider TEXT NOT NULL, model TEXT NOT NULL,
                    output_text TEXT, output_bytes BLOB, output_mime_type TEXT, output_filename TEXT,
                    output_metadata_json TEXT NOT NULL DEFAULT '{}', metrics_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL, expires_at TEXT, hits INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_provider_cache_expiry ON provider_cache(expires_at);
                CREATE TABLE IF NOT EXISTS provider_cache_locks (
                    cache_key TEXT PRIMARY KEY, token TEXT NOT NULL, expires_at REAL NOT NULL
                );
            """)

    def get(self, cache_key: str) -> ProviderCacheEntry | None:
        with self.store._lock, self.store.connection:
            row = self.store.connection.execute(
                "SELECT * FROM provider_cache WHERE cache_key=? AND (expires_at IS NULL OR expires_at>?)",
                (cache_key, datetime.now(UTC).isoformat()),
            ).fetchone()
            if row is None:
                return None
            self.store.connection.execute("UPDATE provider_cache SET hits=hits+1 WHERE cache_key=?", (cache_key,))
            return ProviderCacheEntry(
                cache_key=row["cache_key"], provider=row["provider"], model=row["model"],
                output_text=row["output_text"], output_bytes=row["output_bytes"],
                output_mime_type=row["output_mime_type"], output_filename=row["output_filename"],
                output_metadata=json.loads(row["output_metadata_json"] or "{}"),
                metrics={k: float(v) for k, v in json.loads(row["metrics_json"] or "{}").items()},
            )

    def get_or_lock(self, cache_key: str, lock_seconds: int = 30) -> tuple[ProviderCacheEntry | None, str | None]:
        """Return (entry, token); token is owned by this worker when a miss is locked."""
        cached = self.get(cache_key)
        if cached is not None:
            return cached, None
        token = uuid.uuid4().hex
        now = time.time()
        with self.store._lock:
            conn = self.store.connection
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM provider_cache_locks WHERE expires_at<=?", (now,))
                existing = conn.execute("SELECT token FROM provider_cache_locks WHERE cache_key=?", (cache_key,)).fetchone()
                if existing is None:
                    conn.execute("INSERT INTO provider_cache_locks(cache_key,token,expires_at) VALUES(?,?,?)", (cache_key, token, now + lock_seconds))
                    conn.commit()
                    return None, token
                conn.commit()
                return None, None
            except Exception:
                conn.rollback()
                raise

    def release_lock(self, cache_key: str, token: str | None) -> None:
        if not token:
            return
        with self.store._lock, self.store.connection:
            self.store.connection.execute("DELETE FROM provider_cache_locks WHERE cache_key=? AND token=?", (cache_key, token))

    def put(self, cache_key: str, provider: str, model: str, *, output_text: str | None,
            output_bytes: bytes | None, output_mime_type: str | None, output_filename: str | None,
            output_metadata: dict[str, Any], metrics: dict[str, float]) -> bool:
        if output_bytes is not None and len(output_bytes) > self.max_bytes:
            return False
        if output_bytes is None and not (output_text and output_text.strip()):
            return False
        expires_at = (datetime.now(UTC) + timedelta(seconds=self.ttl_seconds)).isoformat()
        with self.store._lock, self.store.connection:
            self.store.connection.execute(
                "INSERT INTO provider_cache(cache_key,provider,model,output_text,output_bytes,output_mime_type,output_filename,output_metadata_json,metrics_json,created_at,expires_at,hits) VALUES(?,?,?,?,?,?,?,?,?,?,?,0) ON CONFLICT(cache_key) DO NOTHING",
                (cache_key, provider, model, output_text, output_bytes, output_mime_type, output_filename,
                 json.dumps(output_metadata, ensure_ascii=False, sort_keys=True), json.dumps(metrics, ensure_ascii=False, sort_keys=True),
                 datetime.now(UTC).isoformat(), expires_at),
            )
            return True

    def purge_expired(self, now: datetime | None = None) -> int:
        cutoff = (now or datetime.now(UTC)).isoformat()
        with self.store._lock, self.store.connection:
            result = self.store.connection.execute("DELETE FROM provider_cache WHERE expires_at IS NOT NULL AND expires_at<=?", (cutoff,))
            return result.rowcount

    def purge_expired_with_stats(self, now: datetime | None = None) -> dict[str, float | int]:
        cutoff = (now or datetime.now(UTC)).isoformat()
        with self.store._lock, self.store.connection:
            row = self.store.connection.execute(
                "SELECT COUNT(*) AS total, COALESCE(SUM(hits),0) AS total_hits, COALESCE(AVG(hits),0) AS avg_hits FROM provider_cache WHERE expires_at IS NOT NULL AND expires_at<=?",
                (cutoff,),
            ).fetchone()
            result = self.store.connection.execute("DELETE FROM provider_cache WHERE expires_at IS NOT NULL AND expires_at<=?", (cutoff,))
            return {"purged": int(result.rowcount), "total_hits_at_death": int(row["total_hits"]), "avg_hits_at_death": float(row["avg_hits"])}

    def stats(self) -> dict[str, int]:
        with self.store._lock:
            row = self.store.connection.execute("SELECT COUNT(*) AS entries, COALESCE(SUM(hits),0) AS hits FROM provider_cache").fetchone()
            return {"entries": int(row["entries"]), "hits": int(row["hits"])}
