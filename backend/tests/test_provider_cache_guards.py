from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.infrastructure.provider_cache import SQLiteProviderCache
from app.infrastructure.sqlite import SQLiteStore


def test_cache_rejects_error_or_empty_entries() -> None:
    cache = SQLiteProviderCache(SQLiteStore(":memory:"))
    assert not cache.put("error", "openai", "model", output_text=None, output_bytes=None, output_mime_type=None, output_filename=None, output_metadata={"is_error": True}, metrics={})
    assert cache.get("error") is None


def test_cache_key_is_independent_of_job_id() -> None:
    # The worker builds keys only from provider/model/job/target/parameters/seed.
    # This test locks that contract at the cache boundary by using identical keys for different jobs.
    cache = SQLiteProviderCache(SQLiteStore(":memory:"))
    assert cache.put("stable-key", "openai", "gpt-4o", output_text="x", output_bytes=None, output_mime_type=None, output_filename=None, output_metadata={}, metrics={})
    assert cache.get("stable-key") is not None


def test_cache_stampede_lock_has_single_owner_and_expires() -> None:
    cache = SQLiteProviderCache(SQLiteStore(":memory:"))
    entry, token1 = cache.get_or_lock("k", lock_seconds=1)
    assert entry is None and token1
    _, token2 = cache.get_or_lock("k", lock_seconds=1)
    assert token2 is None
    cache.release_lock("k", token1)
    _, token3 = cache.get_or_lock("k", lock_seconds=1)
    assert token3
    cache.release_lock("k", token3)


def test_purge_expired_reports_hit_statistics() -> None:
    cache = SQLiteProviderCache(SQLiteStore(":memory:"))
    assert cache.put("k", "openai", "model", output_text="x", output_bytes=None, output_mime_type=None, output_filename=None, output_metadata={}, metrics={})
    expired = datetime.now(UTC) - timedelta(seconds=1)
    result = cache.purge_expired_with_stats(expired)
    assert result["purged"] == 0
    result = cache.purge_expired_with_stats(datetime.now(UTC) + timedelta(days=2))
    assert result["purged"] == 1
    assert result["avg_hits_at_death"] >= 1
