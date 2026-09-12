from __future__ import annotations

import hashlib
import json
import os
import time
import uuid

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob, JobType
from ..domain.provider_runs import ProviderRun
from ..infrastructure.error_classifier import ErrorKind, classify_exception, classify_provider_response
from ..infrastructure.provider_cache import SQLiteProviderCache
from ..infrastructure.provider_run_repository import SQLiteProviderRunRepository
from ..infrastructure.resilience import SQLiteCircuitBreaker
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext
from ..providers.contracts import ProviderRequest, ProviderResponse
from ..providers.media import media_mime
from ..providers.registry import ModelRegistry


class ProviderGenerationWorker(Worker):
    """Execute real providers with cache and shared circuit protection."""

    worker_type = "provider-generation"
    _TEXT_JOB_TYPES = {JobType.STORY, JobType.SCENE, JobType.SHOT, JobType.CHARACTER, JobType.WORLD}

    def __init__(self, providers: ModelRegistry, storage: LocalAssetStorage, assets: AssetRepository, provider_runs: SQLiteProviderRunRepository | None = None) -> None:
        self.providers = providers
        self.storage = storage
        self.assets = assets
        self.provider_runs = provider_runs
        self._cache: SQLiteProviderCache | None = None
        self._breakers: dict[str, SQLiteCircuitBreaker] = {}
        self._initialized = False

    def initialize(self) -> None:
        store = getattr(self.assets, "store", None)
        if store is not None:
            ttl = int(os.getenv("AICF_PROVIDER_CACHE_TTL_SECONDS", "86400"))
            max_bytes = int(os.getenv("AICF_PROVIDER_CACHE_MAX_BYTES", str(20 * 1024 * 1024)))
            self._cache = SQLiteProviderCache(store, ttl_seconds=ttl, max_bytes=max_bytes)
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized

    def _breaker(self, provider: str, model: str) -> SQLiteCircuitBreaker | None:
        if self._cache is None:
            return None
        key = f"{provider}:{model}"
        if key not in self._breakers:
            self._breakers[key] = SQLiteCircuitBreaker(
                self._cache.store,
                key,
                fail_threshold=int(os.getenv("AICF_CIRCUIT_FAIL_THRESHOLD", "5")),
                open_duration=float(os.getenv("AICF_CIRCUIT_OPEN_DURATION_SECONDS", "60")),
                half_open_max_calls=int(os.getenv("AICF_CIRCUIT_HALF_OPEN_MAX_CALLS", "2")),
                success_threshold=int(os.getenv("AICF_CIRCUIT_SUCCESS_THRESHOLD", "2")),
            )
        return self._breakers[key]

    def _release_cache_lock(self, cache_key: str, lock_token: str | None) -> None:
        if self._cache is not None and lock_token is not None:
            self._cache.release_lock(cache_key, lock_token)

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        if context.cancellation_requested:
            return JobExecutionResult(False, error_code="CANCELLED", error_message="Cancellation requested")

        capability = self._required_capability(job.type)
        model = self.providers.get(job.model) if job.model else None
        if model is None or capability not in model.adapter.capability().capabilities:
            model = self.providers.route("generation", capability)
        if model is None:
            return JobExecutionResult(False, error_code="MODEL_CAPABILITY_UNAVAILABLE", error_message=f"No real provider configured for {capability}", retryable=False)
        if not model.enabled or not model.adapter.health_check():
            return JobExecutionResult(False, error_code="MODEL_UNHEALTHY", error_message=model.id, retryable=True)

        cache_key = self._cache_key(model.provider, model.id, job)
        cached = self._cache.get(cache_key) if self._cache else None
        lock_token: str | None = None
        if cached is None and self._cache is not None:
            cached, lock_token = self._cache.get_or_lock(
                cache_key,
                lock_seconds=int(os.getenv("AICF_PROVIDER_CACHE_LOCK_SECONDS", "30")),
            )
            if cached is None and lock_token is None:
                time.sleep(float(os.getenv("AICF_PROVIDER_CACHE_WAIT_SECONDS", "2")))
                cached = self._cache.get(cache_key)

        if cached is not None:
            response = ProviderResponse(
                success=True,
                output_text=cached.output_text,
                output_bytes=cached.output_bytes,
                output_mime_type=cached.output_mime_type,
                output_filename=cached.output_filename,
                output_metadata={**cached.output_metadata, "cacheHit": True},
                metrics={**cached.metrics, "cache_hit": 1.0},
                provider_run_id=f"cache:{cache_key[:16]}",
            )
            asset_ids = self._materialize_response(job, model.provider, model.id, response, response.provider_run_id or "cache")
            self._release_cache_lock(cache_key, lock_token)
            if not asset_ids:
                return JobExecutionResult(False, error_code="PROVIDER_CACHE_ENTRY_INVALID", error_message="Cached response contained no usable output", retryable=False)
            return JobExecutionResult(True, asset_ids=asset_ids, metrics={**cached.metrics, "cache_hit": 1.0}, provider_run_id=response.provider_run_id)

        breaker = self._breaker(model.provider, model.id)
        if breaker is not None and not breaker.acquire():
            self._release_cache_lock(cache_key, lock_token)
            return JobExecutionResult(False, error_code="PROVIDER_CIRCUIT_OPEN", error_message=f"Circuit open for {model.provider}:{model.id}", retryable=True)

        run_id = str(uuid.uuid4())
        if self.provider_runs:
            self.provider_runs.create(
                ProviderRun(
                    id=run_id,
                    job_id=job.id,
                    provider=model.provider,
                    model=model.id,
                    request_metadata={"jobType": job.type.value, "targetType": job.target_type, "targetId": job.target_id, "capability": capability},
                    status="RUNNING",
                )
            )
        try:
            response = model.adapter.execute(ProviderRequest(model=model.id, parameters=dict(job.input.parameters), seed=job.input.seed))
        except Exception as exc:
            kind = classify_exception(exc)
            if breaker is not None and kind is ErrorKind.TRANSIENT:
                breaker.record_failure()
            self._release_cache_lock(cache_key, lock_token)
            if self.provider_runs:
                self.provider_runs.complete(run_id, status="FAILED", error_code="PROVIDER_EXCEPTION", response_metadata={"exceptionType": type(exc).__name__})
            return JobExecutionResult(False, provider_run_id=run_id, error_code="PROVIDER_EXCEPTION", error_message=str(exc), retryable=kind is ErrorKind.TRANSIENT)

        provider_run_id = response.provider_run_id or run_id
        if not response.success:
            kind = classify_provider_response(response.error_code, response.error_message)
            if breaker is not None and kind is ErrorKind.TRANSIENT:
                breaker.record_failure()
            self._release_cache_lock(cache_key, lock_token)
            if self.provider_runs:
                self.provider_runs.complete(run_id, status="FAILED", error_code=response.error_code or "PROVIDER_FAILED", response_metadata=dict(response.metrics))
            return JobExecutionResult(False, provider_run_id=provider_run_id, error_code=response.error_code or "PROVIDER_FAILED", error_message=response.error_message or "Provider execution failed", retryable=kind is ErrorKind.TRANSIENT)

        asset_ids = self._materialize_response(job, model.provider, model.id, response, provider_run_id)
        if not asset_ids:
            self._release_cache_lock(cache_key, lock_token)
            if self.provider_runs:
                self.provider_runs.complete(run_id, status="FAILED", error_code="PROVIDER_OUTPUT_INVALID", response_metadata={})
            return JobExecutionResult(False, provider_run_id=provider_run_id, error_code="PROVIDER_OUTPUT_INVALID", error_message="Provider returned no usable output", retryable=False)

        if breaker is not None:
            breaker.record_success()
        if self._cache:
            self._cache.put(
                cache_key,
                model.provider,
                model.id,
                output_text=response.output_text,
                output_bytes=response.output_bytes,
                output_mime_type=response.output_mime_type,
                output_filename=response.output_filename,
                output_metadata=dict(response.output_metadata),
                metrics=dict(response.metrics),
            )
            self._release_cache_lock(cache_key, lock_token)
        if self.provider_runs:
            self.provider_runs.complete(run_id, status="COMPLETED", response_metadata={"assetIds": asset_ids, **dict(response.metrics)})
        return JobExecutionResult(True, asset_ids=asset_ids, metrics=dict(response.metrics), provider_run_id=provider_run_id)

    def _materialize_response(self, job: GenerationJob, provider: str, model: str, response: ProviderResponse, provider_run_id: str) -> list[str]:
        asset_ids = list(response.output_asset_ids)
        if asset_ids:
            return asset_ids if self._validate_existing_assets(job, asset_ids) is None else []
        if response.output_bytes is not None:
            if not response.output_bytes:
                return []
            return [self._persist_media(job, provider, model, response, provider_run_id)]
        if job.type not in self._TEXT_JOB_TYPES or not response.output_text or not response.output_text.strip():
            return []
        payload = self._serialize_output(job, response.output_text, response.metrics)
        digest, path, size = self._store(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"provider-asset:{job.id}:{digest}"))
        self.assets.create(
            Asset(
                id=asset_id,
                project_id=job.project_id,
                type=self._asset_type(job),
                path=path,
                mime_type="application/json; charset=utf-8",
                size_bytes=size,
                sha256=digest,
                status=AssetStatus.READY,
                provenance=build_provenance(
                    job,
                    metadata={"provider": provider, "model": model, "providerRunId": provider_run_id},
                    license_status=LicenseStatus.VERIFIED,
                    provider=provider,
                    model=model,
                ),
            )
        )
        return [asset_id]

    def _validate_existing_assets(self, job: GenerationJob, asset_ids: list[str]) -> tuple[str, str, bool] | None:
        expected_type = self._asset_type(job)
        for asset_id in asset_ids:
            asset = self.assets.get(asset_id)
            if asset is None or asset.project_id != job.project_id or asset.status is not AssetStatus.READY or asset.type is not expected_type:
                return ("PROVIDER_ASSET_INVALID", f"Invalid provider asset: {asset_id}", False)
            try:
                if not self.storage.verify(asset):
                    return ("PROVIDER_ASSET_INTEGRITY_FAILED", f"Provider asset failed storage verification: {asset_id}", False)
            except (OSError, IOError, ValueError):
                return ("PROVIDER_ASSET_INTEGRITY_FAILED", f"Provider asset failed storage verification: {asset_id}", False)
        return None

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False

    def _persist_media(self, job: GenerationJob, provider: str, model: str, response: ProviderResponse, provider_run_id: str) -> str:
        data = response.output_bytes or b""
        digest, path, size = self._store(data)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"provider-media:{job.id}:{digest}"))
        metadata = {"provider": provider, "model": model, "providerRunId": provider_run_id, **dict(response.output_metadata)}
        self.assets.create(
            Asset(
                id=asset_id,
                project_id=job.project_id,
                type=self._asset_type(job),
                path=path,
                mime_type=response.output_mime_type or media_mime(job.type.value, job.input.parameters),
                size_bytes=size,
                sha256=digest,
                status=AssetStatus.READY,
                provenance=build_provenance(
                    job,
                    metadata=metadata,
                    license_status=LicenseStatus.VERIFIED,
                    provider=provider,
                    model=model,
                ),
            )
        )
        return asset_id

    def _store(self, payload: bytes) -> tuple[str, str, int]:
        digest = hashlib.sha256(payload).hexdigest()
        _, path, size = self.storage.put_bytes(payload)
        return digest, path, size

    @staticmethod
    def _cache_key(provider: str, model: str, job: GenerationJob) -> str:
        payload = {"provider": provider, "model": model, "jobType": job.type.value, "targetType": job.target_type, "parameters": job.input.parameters, "seed": job.input.seed}
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _serialize_output(job: GenerationJob, output_text: str | None, metrics: dict[str, float]) -> bytes:
        return (json.dumps({"jobId": job.id, "jobType": job.type.value, "targetId": job.target_id, "output": output_text, "metrics": metrics}, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")

    @staticmethod
    def _required_capability(job_type: JobType) -> str:
        return {JobType.IMAGE: "image", JobType.VIDEO: "video", JobType.TTS: "tts", JobType.LIPSYNC: "lipsync", JobType.MUSIC: "music", JobType.SFX: "sfx", JobType.STORY: "story", JobType.SCENE: "scene", JobType.SHOT: "shot", JobType.CHARACTER: "character", JobType.WORLD: "world"}.get(job_type, "generation")

    @staticmethod
    def _asset_type(job: GenerationJob) -> AssetType:
        if job.type.value in {"IMAGE", "THUMBNAIL"}:
            return AssetType.IMAGE
        if job.type.value in {"VIDEO", "RENDER"}:
            return AssetType.VIDEO
        if job.type.value in {"TTS", "MUSIC", "SFX", "LIPSYNC"}:
            return AssetType.AUDIO
        if job.type.value == "SUBTITLE":
            return AssetType.SUBTITLE
        return AssetType.DOCUMENT
