from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.jobs import GenerationJob, JobInput, JobType, JobStatus
from app.infrastructure.provider_cache import SQLiteProviderCache
from app.infrastructure.sqlite import SQLiteRepositories
from app.workers.provider_worker import ProviderGenerationWorker


def _job(job_id: str, parameters: dict) -> GenerationJob:
    return GenerationJob(
        id=job_id,
        project_id="project-1",
        type=JobType.IMAGE,
        target_type="shot",
        target_id="shot-1",
        status=JobStatus.QUEUED,
        priority=10,
        input=JobInput(parameters=parameters),
    )


def test_provider_cache_key_changes_when_provider_model_or_parameters_change() -> None:
    first = ProviderGenerationWorker._cache_key("openai", "image-model", _job("a", {"prompt": "cat", "size": "1024x1024"}))
    same_request = ProviderGenerationWorker._cache_key("openai", "image-model", _job("b", {"size": "1024x1024", "prompt": "cat"}))
    different_model = ProviderGenerationWorker._cache_key("openai", "other-model", _job("c", {"prompt": "cat", "size": "1024x1024"}))
    different_prompt = ProviderGenerationWorker._cache_key("openai", "image-model", _job("d", {"prompt": "dog", "size": "1024x1024"}))

    assert first == same_request
    assert first != different_model
    assert first != different_prompt


def test_provider_cache_stores_success_and_counts_hits() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        cache = SQLiteProviderCache(repositories.store, ttl_seconds=3600)
        assert cache.put(
            "key-1", "openai", "image-model",
            output_text=None,
            output_bytes=b"real-image",
            output_mime_type="image/png",
            output_filename="image.png",
            output_metadata={"quality": "high"},
            metrics={"latency_ms": 123.0},
        )
        entry = cache.get("key-1")
        assert entry is not None
        assert entry.output_bytes == b"real-image"
        assert entry.output_mime_type == "image/png"
        assert cache.stats() == {"entries": 1, "hits": 1}
    finally:
        repositories.close()


def test_provider_cache_expires_and_purge_removes_it() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        cache = SQLiteProviderCache(repositories.store, ttl_seconds=1)
        assert cache.put(
            "key-expire", "openai", "text-model",
            output_text="hello",
            output_bytes=None,
            output_mime_type=None,
            output_filename=None,
            output_metadata={},
            metrics={},
        )
        future = datetime.now(UTC) + timedelta(seconds=2)
        assert cache.get("key-expire") is not None
        assert cache.purge_expired(future) == 1
        assert cache.get("key-expire") is None
    finally:
        repositories.close()


def test_provider_cache_skips_oversized_binary_payload() -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        cache = SQLiteProviderCache(repositories.store, max_bytes=4)
        assert not cache.put(
            "key-large", "local", "video-model",
            output_text=None,
            output_bytes=b"12345",
            output_mime_type="video/mp4",
            output_filename="video.mp4",
            output_metadata={},
            metrics={},
        )
        assert cache.get("key-large") is None
    finally:
        repositories.close()
