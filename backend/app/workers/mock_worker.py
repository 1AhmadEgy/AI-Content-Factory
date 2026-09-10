from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetProvenance, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext


class DeterministicMockWorker(Worker):
    """Offline worker that creates real, checksum-verifiable fixture assets."""

    worker_type = "mock"

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository) -> None:
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

        payload = self._payload(job)
        digest, path, size = self.storage.put_bytes(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"mock-asset:{job.id}:{digest}"))
        asset = Asset(
            id=asset_id,
            project_id=job.project_id,
            type=self._asset_type(job),
            path=path,
            mime_type="text/plain; charset=utf-8",
            size_bytes=size,
            sha256=digest,
            status=AssetStatus.READY,
            provenance=build_provenance(
                job,
                metadata={"deterministic": True, "workerType": self.worker_type},
            ),
        )
        self.assets.create(asset)
        return JobExecutionResult(
            success=True,
            asset_ids=[asset.id],
            metrics={"bytes": size, "sha256": digest},
            provider_run_id=f"mock-run-{job.id}",
        )

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False

    @staticmethod
    def _payload(job: GenerationJob) -> bytes:
        seed = job.input.seed if job.input.seed is not None else 0
        material = f"job={job.id}|type={job.type.value}|seed={seed}|params={sorted(job.input.parameters.items())}"
        checksum = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return (f"AI-Content-Factory mock asset\n{material}\nsha256={checksum}\n").encode("utf-8")

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
