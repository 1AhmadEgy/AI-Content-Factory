from __future__ import annotations

import hashlib
import json
import uuid

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob
from ..domain.provider_runs import ProviderRun
from ..infrastructure.provider_run_repository import SQLiteProviderRunRepository
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext
from ..providers.contracts import ProviderRequest
from ..providers.registry import ModelRegistry
from ..providers.media import media_mime

class ProviderGenerationWorker(Worker):
    worker_type = "provider-generation"
    def __init__(self, providers: ModelRegistry, storage: LocalAssetStorage, assets: AssetRepository, provider_runs: SQLiteProviderRunRepository | None = None) -> None:
        self.providers, self.storage, self.assets, self.provider_runs = providers, storage, assets, provider_runs
        self._initialized = False
    def initialize(self) -> None: self._initialized = True
    def health_check(self) -> bool: return self._initialized
    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized: return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        if context.cancellation_requested: return JobExecutionResult(False, error_code="CANCELLED", error_message="Cancellation requested")
        model = self.providers.get(job.model) if job.model else self.providers.route("generation", job.type.value.lower())
        if model is None: return JobExecutionResult(False, error_code="MODEL_UNAVAILABLE", error_message=f"No model for {job.type.value}", retryable=True)
        if not model.enabled or not model.adapter.health_check(): return JobExecutionResult(False, error_code="MODEL_UNHEALTHY", error_message=model.id, retryable=True)
        run_id = str(uuid.uuid4())
        if self.provider_runs: self.provider_runs.create(ProviderRun(id=run_id, job_id=job.id, provider=model.provider, model=model.id, request_metadata={"jobType": job.type.value, "targetType": job.target_type, "targetId": job.target_id}, status="RUNNING"))
        try: response = model.adapter.execute(ProviderRequest(model=model.id, parameters=dict(job.input.parameters), seed=job.input.seed))
        except Exception as exc:
            if self.provider_runs: self.provider_runs.complete(run_id, status="FAILED", error_code="PROVIDER_EXCEPTION", response_metadata={"exceptionType": type(exc).__name__})
            return JobExecutionResult(False, provider_run_id=run_id, error_code="PROVIDER_EXCEPTION", error_message=str(exc), retryable=True)
        provider_run_id = response.provider_run_id or run_id
        if not response.success:
            if self.provider_runs: self.provider_runs.complete(run_id, status="FAILED", error_code=response.error_code or "PROVIDER_FAILED", response_metadata=dict(response.metrics))
            return JobExecutionResult(False, provider_run_id=provider_run_id, error_code=response.error_code or "PROVIDER_FAILED", error_message=response.error_message or "Provider execution failed", retryable=True)
        asset_ids = list(response.output_asset_ids)
        if not asset_ids and response.output_bytes is not None: asset_ids = [self._persist_media(job, model.provider, model.id, response, provider_run_id)]
        if not asset_ids:
            payload = self._serialize_output(job, response.output_text, response.metrics); digest, path, size = self._store(payload); asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"provider-asset:{job.id}:{digest}"))
            provenance = build_provenance(job, metadata={"provider": model.provider, "model": model.id, "providerRunId": provider_run_id}, license_status=LicenseStatus.VERIFIED); provenance.provider = model.provider; provenance.model = model.id
            self.assets.create(Asset(id=asset_id, project_id=job.project_id, type=self._asset_type(job), path=path, mime_type="application/json; charset=utf-8", size_bytes=size, sha256=digest, status=AssetStatus.READY, provenance=provenance)); asset_ids = [asset_id]
        if self.provider_runs: self.provider_runs.complete(run_id, status="COMPLETED", response_metadata={"assetIds": asset_ids, **dict(response.metrics)})
        return JobExecutionResult(success=True, asset_ids=asset_ids, metrics=dict(response.metrics), provider_run_id=provider_run_id)
    def cancel(self, job_id: str) -> None: return None
    def shutdown(self) -> None: self._initialized = False
    def _persist_media(self, job: GenerationJob, provider: str, model: str, response, provider_run_id: str) -> str:
        data = response.output_bytes or b""; digest, path, size = self._store(data); asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"provider-media:{job.id}:{digest}")); metadata = {"provider": provider, "model": model, "providerRunId": provider_run_id, **dict(response.output_metadata)}
        provenance = build_provenance(job, metadata=metadata, license_status=LicenseStatus.VERIFIED); provenance.provider = provider; provenance.model = model
        self.assets.create(Asset(id=asset_id, project_id=job.project_id, type=self._asset_type(job), path=path, mime_type=response.output_mime_type or media_mime(job.type.value, job.input.parameters), size_bytes=size, sha256=digest, status=AssetStatus.READY, provenance=provenance)); return asset_id
    def _store(self, payload: bytes) -> tuple[str, str, int]:
        digest = hashlib.sha256(payload).hexdigest(); _, path, size = self.storage.put_bytes(payload); return digest, path, size
    @staticmethod
    def _serialize_output(job: GenerationJob, output_text: str | None, metrics: dict[str, float]) -> bytes:
        return (json.dumps({"jobId": job.id, "jobType": job.type.value, "targetId": job.target_id, "output": output_text, "metrics": metrics}, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    @staticmethod
    def _asset_type(job: GenerationJob) -> AssetType:
        if job.type.value in {"IMAGE", "THUMBNAIL"}: return AssetType.IMAGE
        if job.type.value in {"VIDEO", "RENDER"}: return AssetType.VIDEO
        if job.type.value in {"TTS", "MUSIC", "SFX", "LIPSYNC"}: return AssetType.AUDIO
        if job.type.value == "SUBTITLE": return AssetType.SUBTITLE
        return AssetType.DOCUMENT
