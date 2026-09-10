from __future__ import annotations

import hashlib
import json
import uuid

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext
from ..providers.contracts import ProviderRequest
from ..providers.registry import ModelRegistry


class ProviderGenerationWorker(Worker):
    """Execute generation jobs through the model registry and persist outputs."""

    worker_type = "provider-generation"

    def __init__(self, providers: ModelRegistry, storage: LocalAssetStorage, assets: AssetRepository) -> None:
        self.providers = providers
        self.storage = storage
        self.assets = assets
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

        request = ProviderRequest(model=model.id, parameters=dict(job.input.parameters), seed=job.input.seed)
        response = model.adapter.execute(request)
        if not response.success:
            return JobExecutionResult(
                False,
                provider_run_id=response.provider_run_id,
                error_code=response.error_code or "PROVIDER_FAILED",
                error_message=response.error_message or "Provider execution failed",
                retryable=True,
            )

        asset_ids = list(response.output_asset_ids)
        if not asset_ids:
            payload = self._serialize_output(job, response.output_text, response.metrics)
            digest, path, size = self._store(payload)
            asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"provider-asset:{job.id}:{digest}"))
            asset = Asset(
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
                    metadata={"provider": model.provider, "model": model.id, "providerRunId": response.provider_run_id},
                    license_status=LicenseStatus.VERIFIED,
                ),
            )
            self.assets.create(asset)
            asset_ids = [asset_id]

        return JobExecutionResult(
            success=True,
            asset_ids=asset_ids,
            metrics=dict(response.metrics),
            provider_run_id=response.provider_run_id,
        )

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False

    def _store(self, payload: bytes) -> tuple[str, str, int]:
        digest = hashlib.sha256(payload).hexdigest()
        _, path, size = self.storage.put_bytes(payload)
        return digest, path, size

    @staticmethod
    def _serialize_output(job: GenerationJob, output_text: str | None, metrics: dict[str, float]) -> bytes:
        return (json.dumps({
            "jobId": job.id,
            "jobType": job.type.value,
            "targetId": job.target_id,
            "output": output_text,
            "metrics": metrics,
        }, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")

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
