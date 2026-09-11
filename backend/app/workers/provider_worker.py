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
from ..providers.media import media_mime
from ..providers.registry import ModelRegistry


class ProviderGenerationWorker(Worker):
    """Execute generation jobs and persist provider outputs plus run telemetry."""

    worker_type = "provider-generation"

    def __init__(self, providers: ModelRegistry, storage: LocalAssetStorage, assets: AssetRepository,
                 provider_runs: SQLiteProviderRunRepository | None = None) -> None:
        self.providers = providers
        self.storage = storage
        self.assets = assets
        self.provider_runs = provider_runs
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        if context.cancellation_requested:
            return JobExecutionResult(False, error_code="CANCELLED", error_message="Cancellation requested")
        model = self.providers.get(job.model) if job.model else self.providers.route("generation", job.type.value.lower())
        if model is None:
            return JobExecutionResult(False, error_code="MODEL_UNAVAILABLE", error_message=f"No model for {job.type.value}", retryable=True)
        if not model.enabled or not model.adapter.health_check():
            return JobExecutionResult(False, error_code="MODEL_UNHEALTHY", error_message=model.id, retryable=True)

        internal_run_id = str(uuid.uuid4())
        if self.provider_runs:
            self.provider_runs.create(ProviderRun(
                id=internal_run_id, job_id=job.id, provider=model.provider, model=model.id,
                request_metadata={"jobType": job.type.value, "targetType": job.target_type, "targetId": job.target_id},
                status="RUNNING",
            ))
        try:
            response = model.adapter.execute(ProviderRequest(model=model.id, parameters=dict(job.input.parameters), seed=job.input.seed))
        except Exception as exc:
            if self.provider_runs:
                self.provider_runs.complete(internal_run_id, status="FAILED", error_code="PROVIDER_EXCEPTION", response_metadata={"exceptionType": type(exc).__name__})
            return JobExecutionResult(False, error_code="PROVIDER_EXCEPTION", error_message=str(exc), retryable=True)

        provider_run_id = response.provider_run_id
        if not response.success:
            if self.provider_runs:
                self.provider_runs.complete(internal_run_id, status="FAILED", error_code=response.error_code or "PROVIDER_FAILED", response_metadata=dict(response.metrics))
            return JobExecutionResult(False, provider_run_id=provider_run_id, error_code=response.error_code or "PROVIDER_FAILED", error_message=response.error_message or "Provider execution failed", retryable=True)

        if not isinstance(provider_run_id, str) or not provider_run_id.strip():
            if self.provider_runs:
                self.provider_runs.complete(internal_run_id, status="FAILED", error_code="PROVIDER_RUN_ID_MISSING", response_metadata=dict(response.metrics))
            return JobExecutionResult(False, error_code="PROVIDER_RUN_ID_MISSING", error_message="Provider reported success without a provider run id", retryable=True)
        provider_run_id = provider_run_id.strip()

        asset_ids = list(response.output_asset_ids)
        if asset_ids:
            invalid_asset = self._validate_existing_assets(job, asset_ids)
            if invalid_asset:
                if self.provider_runs:
                    self.provider_runs.complete(internal_run_id, status="FAILED", error_code=invalid_asset[0], response_metadata={"assetId": invalid_asset[1]})
                return JobExecutionResult(False, provider_run_id=provider_run_id, error_code=invalid_asset[0], error_message=invalid_asset[2], retryable=True)
        elif response.output_bytes is not None:
            if not response.output_bytes:
                return self._fail_provider_run(internal_run_id, provider_run_id, "PROVIDER_EMPTY_OUTPUT", "Provider returned empty binary output")
            asset_ids = [self._persist_media(job, model.provider, model.id, response, provider_run_id)]
        elif response.output_text is not None and response.output_text.strip():
            payload = self._serialize_output(job, response.output_text, response.metrics)
            digest, path, size = self._store(payload)
            asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"provider-asset:{job.id}:{digest}"))
            self.assets.create(Asset(id=asset_id, project_id=job.project_id, type=self._asset_type(job), path=path, mime_type="application/json; charset=utf-8", size_bytes=size, sha256=digest, status=AssetStatus.READY, provenance=build_provenance(job, metadata={"provider": model.provider, "model": model.id, "providerRunId": provider_run_id}, license_status=LicenseStatus.VERIFIED)))
            asset_ids = [asset_id]
        else:
            return self._fail_provider_run(internal_run_id, provider_run_id, "PROVIDER_EMPTY_OUTPUT", "Provider reported success without an asset or output")

        if self.provider_runs:
            self.provider_runs.complete(internal_run_id, status="COMPLETED", response_metadata={"assetIds": asset_ids, "providerRunId": provider_run_id, **dict(response.metrics)})
        return JobExecutionResult(success=True, asset_ids=asset_ids, metrics=dict(response.metrics), provider_run_id=provider_run_id)

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False

    def _fail_provider_run(self, internal_run_id: str, provider_run_id: str, error_code: str, message: str) -> JobExecutionResult:
        if self.provider_runs:
            self.provider_runs.complete(internal_run_id, status="FAILED", error_code=error_code)
        return JobExecutionResult(False, provider_run_id=provider_run_id, error_code=error_code, error_message=message, retryable=True)

    def _validate_existing_assets(self, job: GenerationJob, asset_ids: list[str]) -> tuple[str, str, str] | None:
        expected_type = self._asset_type(job)
        for asset_id in asset_ids:
            asset = self.assets.get(asset_id)
            if asset is None:
                return "PROVIDER_ASSET_NOT_FOUND", asset_id, "Provider referenced an asset that does not exist"
            if asset.project_id != job.project_id:
                return "PROVIDER_ASSET_PROJECT_MISMATCH", asset_id, "Provider asset belongs to another project"
            if asset.status != AssetStatus.READY:
                return "PROVIDER_ASSET_NOT_READY", asset_id, "Provider asset is not READY"
            if asset.type != expected_type:
                return "PROVIDER_ASSET_TYPE_MISMATCH", asset_id, "Provider asset type does not match the generation job"
            if not self.storage.verify(asset):
                return "PROVIDER_ASSET_INTEGRITY_FAILED", asset_id, "Provider asset failed storage integrity verification"
        return None

    def _persist_media(self, job: GenerationJob, provider: str, model: str, response, provider_run_id: str) -> str:
        data = response.output_bytes or b""
        digest, path, size = self._store(data)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"provider-media:{job.id}:{digest}"))
        metadata = {"provider": provider, "model": model, "providerRunId": provider_run_id, **dict(response.output_metadata)}
        self.assets.create(Asset(id=asset_id, project_id=job.project_id, type=self._asset_type(job), path=path, mime_type=response.output_mime_type or media_mime(job.type.value, job.input.parameters), size_bytes=size, sha256=digest, status=AssetStatus.READY, provenance=build_provenance(job, metadata=metadata, license_status=LicenseStatus.VERIFIED)))
        return asset_id

    def _store(self, payload: bytes) -> tuple[str, str, int]:
        digest = hashlib.sha256(payload).hexdigest()
        _, path, size = self.storage.put_bytes(payload)
        return digest, path, size

    @staticmethod
    def _serialize_output(job: GenerationJob, output_text: str, metrics: dict[str, float]) -> bytes:
        return (json.dumps({"jobId": job.id, "jobType": job.type.value, "targetId": job.target_id, "output": output_text, "metrics": metrics}, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")

    @staticmethod
    def _asset_type(job: GenerationJob) -> AssetType:
        if job.type.value in {"IMAGE", "THUMBNAIL"}: return AssetType.IMAGE
        if job.type.value in {"VIDEO", "RENDER"}: return AssetType.VIDEO
        if job.type.value in {"TTS", "MUSIC", "SFX", "LIPSYNC"}: return AssetType.AUDIO
        if job.type.value == "SUBTITLE": return AssetType.SUBTITLE
        return AssetType.DOCUMENT
