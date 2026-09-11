from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext


class QualityControlWorker(Worker):
    """Run real filesystem/asset QC and fail closed when an asset is invalid."""

    worker_type = "quality-control"

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
        asset_ids = list(job.input.reference_asset_ids)
        if not asset_ids:
            return JobExecutionResult(False, error_code="QC_NO_ASSETS", error_message="No assets supplied for QC")

        checks = []
        for asset_id in asset_ids:
            asset = self.assets.get(asset_id)
            path_exists = bool(asset and Path(asset.path).is_file())
            non_empty = bool(asset and asset.size_bytes > 0 and path_exists)
            checks.append({
                "assetId": asset_id,
                "exists": asset is not None,
                "ready": bool(asset and asset.status is AssetStatus.READY),
                "pathExists": path_exists,
                "nonEmpty": non_empty,
                "checksum": bool(asset and asset.sha256),
                "licenseVerified": bool(asset and asset.provenance.license_status is LicenseStatus.VERIFIED),
            })
        valid = [c for c in checks if c["exists"] and c["ready"] and c["pathExists"] and c["nonEmpty"] and c["checksum"]]
        score = round(100.0 * len(valid) / len(checks), 2)
        passed = score == 100.0
        report = {"jobId": job.id, "assetIds": asset_ids, "checks": checks, "score": score, "passed": passed}
        payload = (json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        _, path, size = self.storage.put_bytes(payload)
        report_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"qc-report:{job.id}:{digest}"))
        report_asset = Asset(
            id=report_id,
            project_id=job.project_id,
            type=AssetType.DOCUMENT,
            path=path,
            mime_type="application/json; charset=utf-8",
            size_bytes=size,
            sha256=digest,
            status=AssetStatus.READY,
            provenance=build_provenance(job, source_asset_ids=asset_ids, metadata={"score": score, "passed": passed}, license_status=LicenseStatus.VERIFIED),
        )
        self.assets.create(report_asset)
        if not passed:
            return JobExecutionResult(False, asset_ids=[report_id], metrics={"score": score, "passed": 0.0}, provider_run_id=f"qc-{job.id}", error_code="QC_FAILED", error_message=f"Technical QC failed with score {score}", retryable=False)
        return JobExecutionResult(success=True, asset_ids=[report_id], metrics={"score": score, "passed": 1.0}, provider_run_id=f"qc-{job.id}")

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
