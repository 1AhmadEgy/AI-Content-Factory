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


class PublishWorker(Worker):
    """Persist a provider-neutral publication package; platform adapters can consume it later."""

    worker_type = "publish"

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository) -> None:
        self.storage, self.assets, self._initialized = storage, assets, False

    def initialize(self) -> None:
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        package = {"jobId": job.id, "projectId": job.project_id,
                   "assetIds": list(job.input.reference_asset_ids),
                   "platforms": job.input.parameters.get("platforms", ["youtube", "tiktok", "instagram", "facebook"]),
                   "title": job.input.parameters.get("title", "AI Content"),
                   "description": job.input.parameters.get("description", ""),
                   "tags": job.input.parameters.get("tags", []),
                   "status": "READY_FOR_PLATFORM_PUBLISH"}
        payload = (json.dumps(package, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        digest, path, size = self.storage.put_bytes(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"publish:{job.id}:{digest}"))
        self.assets.create(Asset(asset_id, job.project_id, AssetType.DOCUMENT, path,
                                 "application/json; charset=utf-8", size, digest, AssetStatus.READY,
                                 build_provenance(job, source_asset_ids=list(job.input.reference_asset_ids),
                                                  metadata={"publicationPackage": True}, license_status=LicenseStatus.VERIFIED)))
        return JobExecutionResult(True, [asset_id], {"platformCount": len(package["platforms"])}, f"publish-{job.id}")

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
