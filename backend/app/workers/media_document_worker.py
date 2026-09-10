from __future__ import annotations

import hashlib
import json
import uuid

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob, JobType
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext


class MediaDocumentWorker(Worker):
    """Offline-first worker for subtitles, thumbnails, metadata and final QC reports."""

    worker_type = "media-document"

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository) -> None:
        self.storage, self.assets, self._initialized = storage, assets, False

    def initialize(self) -> None:
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        if job.type is JobType.SUBTITLE:
            return self._document(job, AssetType.SUBTITLE, "text/vtt", self._subtitle(job))
        if job.type is JobType.METADATA:
            return self._document(job, AssetType.DOCUMENT, "application/json; charset=utf-8", self._metadata(job))
        if job.type is JobType.THUMBNAIL:
            return self._document(job, AssetType.THUMBNAIL, "application/json; charset=utf-8", self._thumbnail(job))
        if job.type is JobType.QC:
            return self._document(job, AssetType.DOCUMENT, "application/json; charset=utf-8", self._final_qc(job))
        return JobExecutionResult(False, error_code="UNSUPPORTED_JOB_TYPE", error_message=job.type.value)

    def _document(self, job: GenerationJob, kind: AssetType, mime: str, payload: bytes) -> JobExecutionResult:
        digest, path, size = self.storage.put_bytes(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{job.type.value}:{job.id}:{digest}"))
        asset = Asset(asset_id, job.project_id, kind, path, mime, size, digest, AssetStatus.READY,
                      build_provenance(job, source_asset_ids=list(job.input.reference_asset_ids),
                                       metadata={"worker": self.worker_type}, license_status=LicenseStatus.VERIFIED))
        self.assets.create(asset)
        return JobExecutionResult(True, [asset_id], {"bytes": size}, f"{self.worker_type}-{job.id}")

    @staticmethod
    def _subtitle(job: GenerationJob) -> bytes:
        text = str(job.input.parameters.get("text", job.input.parameters.get("narration", ""))).strip()
        return ("WEBVTT\n\n00:00:00.000 --> 00:00:05.000\n" + text + "\n").encode("utf-8")

    @staticmethod
    def _metadata(job: GenerationJob) -> bytes:
        data = {"projectId": job.project_id, "jobId": job.id, "title": job.input.parameters.get("title", "AI Content"),
                "description": job.input.parameters.get("description", ""), "tags": job.input.parameters.get("tags", []),
                "language": job.input.parameters.get("language", "en"), "platforms": job.input.parameters.get("platforms", [])}
        return (json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")

    @staticmethod
    def _thumbnail(job: GenerationJob) -> bytes:
        data = {"type": "thumbnail", "title": job.input.parameters.get("title", "AI Content"),
                "sourceAssetIds": job.input.reference_asset_ids, "format": "ffmpeg-compatible-source"}
        return (json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")

    def _final_qc(self, job: GenerationJob) -> bytes:
        checks = []
        for asset_id in job.input.reference_asset_ids:
            asset = self.assets.get(asset_id)
            checks.append({"assetId": asset_id, "exists": asset is not None,
                           "ready": bool(asset and asset.status is AssetStatus.READY),
                           "checksum": bool(asset and asset.sha256)})
        passed = bool(checks) and all(c["exists"] and c["ready"] and c["checksum"] for c in checks)
        report = {"jobId": job.id, "stage": "FINAL_QC", "passed": passed, "checks": checks,
                  "score": round(100 * sum(1 for c in checks if c["exists"] and c["ready"] and c["checksum"]) / max(len(checks), 1), 2)}
        return (json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
