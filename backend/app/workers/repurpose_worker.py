from __future__ import annotations

import json
import uuid

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob, JobType
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext


class RepurposeWorker(Worker):
    """Create a structured repurposing plan for long-form content."""

    worker_type = "repurpose"

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository) -> None:
        self.storage, self.assets, self._initialized = storage, assets, False

    def initialize(self) -> None:
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        if job.type is not JobType.REPURPOSE:
            return JobExecutionResult(False, error_code="UNSUPPORTED_JOB_TYPE", error_message=job.type.value)
        platforms = job.input.parameters.get("platforms", ["youtube_shorts", "tiktok", "instagram_reels", "facebook_reels"])
        duration = int(job.input.parameters.get("clipDurationSeconds", 60))
        plan = {"jobId": job.id, "projectId": job.project_id, "sourceAssetIds": list(job.input.reference_asset_ids), "outputs": [{"platform": str(p), "durationSeconds": duration, "aspectRatio": "9:16", "requires": ["caption", "hook", "thumbnail"]} for p in platforms]}
        payload = (json.dumps(plan, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        digest, path, size = self.storage.put_bytes(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"repurpose:{job.id}:{digest}"))
        self.assets.create(Asset(asset_id, job.project_id, AssetType.DOCUMENT, path, "application/json; charset=utf-8", size, digest, AssetStatus.READY, build_provenance(job, source_asset_ids=list(job.input.reference_asset_ids), metadata={"repurposing": True}, license_status=LicenseStatus.VERIFIED)))
        return JobExecutionResult(True, [asset_id], {"outputCount": len(platforms)}, f"repurpose-{job.id}")

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
