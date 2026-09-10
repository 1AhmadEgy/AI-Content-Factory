from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob, JobType
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext


class MediaDocumentWorker(Worker):
    """Offline-first worker for subtitles, real thumbnails, metadata and final media QC."""

    worker_type = "media-document"

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository, ffmpeg_binary: str = "ffmpeg", ffprobe_binary: str = "ffprobe") -> None:
        self.storage, self.assets = storage, assets
        self.ffmpeg_binary, self.ffprobe_binary = ffmpeg_binary, ffprobe_binary
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized

    @staticmethod
    def _progress(context: WorkerContext | None, progress: float, stage: str) -> None:
        if context is not None:
            context.report_progress(progress, stage)

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        self._progress(context, 0.05, "media_prepare")
        if job.type is JobType.SUBTITLE:
            self._progress(context, 0.45, "subtitle_generation")
            result = self._document(job, AssetType.SUBTITLE, "text/vtt; charset=utf-8", self._subtitle(job))
        elif job.type is JobType.METADATA:
            self._progress(context, 0.45, "metadata_generation")
            result = self._document(job, AssetType.DOCUMENT, "application/json; charset=utf-8", self._metadata(job))
        elif job.type is JobType.THUMBNAIL:
            self._progress(context, 0.35, "thumbnail_extract")
            result = self._thumbnail_asset(job)
        elif job.type is JobType.QC:
            self._progress(context, 0.35, "final_qc")
            result = self._final_qc(job)
        else:
            return JobExecutionResult(False, error_code="UNSUPPORTED_JOB_TYPE", error_message=job.type.value)
        if result.success:
            self._progress(context, 1.0, "completed")
        return result

    def _document(self, job: GenerationJob, kind: AssetType, mime: str, payload: bytes) -> JobExecutionResult:
        digest, path, size = self.storage.put_bytes(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{job.type.value}:{job.id}:{digest}"))
        asset = Asset(
            asset_id, job.project_id, kind, path, mime, size, digest, AssetStatus.READY,
            build_provenance(job, source_asset_ids=list(job.input.reference_asset_ids), metadata={"worker": self.worker_type}, license_status=LicenseStatus.VERIFIED),
        )
        self.assets.create(asset)
        return JobExecutionResult(True, [asset_id], {"bytes": size}, f"{self.worker_type}-{job.id}")

    @staticmethod
    def _subtitle(job: GenerationJob) -> bytes:
        text = str(job.input.parameters.get("text", job.input.parameters.get("narration", ""))).strip()
        end = str(job.input.parameters.get("end", "00:00:05.000"))
        return ("WEBVTT\n\n00:00:00.000 --> " + end + "\n" + text + "\n").encode("utf-8")

    @staticmethod
    def _metadata(job: GenerationJob) -> bytes:
        data = {
            "projectId": job.project_id,
            "jobId": job.id,
            "title": job.input.parameters.get("title", "AI Content"),
            "description": job.input.parameters.get("description", ""),
            "tags": job.input.parameters.get("tags", []),
            "language": job.input.parameters.get("language", "en"),
            "platforms": job.input.parameters.get("platforms", []),
            "scheduledAt": job.input.parameters.get("scheduledAt"),
        }
        return (json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")

    def _thumbnail_asset(self, job: GenerationJob) -> JobExecutionResult:
        source = self.assets.get(job.input.reference_asset_ids[0]) if job.input.reference_asset_ids else None
        if source is None:
            return JobExecutionResult(False, error_code="THUMBNAIL_SOURCE_NOT_FOUND", error_message="No source asset")
        if source.status is not AssetStatus.READY:
            return JobExecutionResult(False, error_code="THUMBNAIL_SOURCE_NOT_READY", error_message="Source asset is not ready")
        if source.type is not AssetType.VIDEO:
            return JobExecutionResult(False, error_code="THUMBNAIL_SOURCE_NOT_VIDEO", error_message="Thumbnail source must be a video")
        if shutil.which(self.ffmpeg_binary) is None:
            return JobExecutionResult(False, error_code="FFMPEG_NOT_AVAILABLE", error_message="FFmpeg executable was not found")
        timestamp = str(job.input.parameters.get("timestamp", "00:00:01"))
        with tempfile_directory() as temp:
            input_path = temp / "input.mp4"
            output_path = temp / "thumbnail.jpg"
            input_path.write_bytes(self.storage.read_bytes(source.sha256))
            completed = subprocess.run(
                [self.ffmpeg_binary, "-hide_banner", "-loglevel", "error", "-y", "-ss", timestamp, "-i", str(input_path), "-frames:v", "1", "-q:v", "2", str(output_path)],
                check=False, capture_output=True,
            )
            if completed.returncode != 0 or not output_path.is_file():
                return JobExecutionResult(False, error_code="THUMBNAIL_GENERATION_FAILED", error_message=completed.stderr.decode("utf-8", errors="replace")[-2000:], retryable=True)
            digest, path, size = self.storage.put_bytes(output_path.read_bytes())
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"thumbnail:{job.id}:{digest}"))
        self.assets.create(Asset(
            asset_id, job.project_id, AssetType.THUMBNAIL, path, "image/jpeg", size, digest, AssetStatus.READY,
            build_provenance(job, source_asset_ids=[source.id], metadata={"engine": "ffmpeg", "timestamp": timestamp}, license_status=LicenseStatus.VERIFIED),
        ))
        return JobExecutionResult(True, [asset_id], {"bytes": size, "format": "jpeg", "timestamp": timestamp}, f"thumbnail-{job.id}")

    def _final_qc(self, job: GenerationJob) -> JobExecutionResult:
        checks = []
        ffprobe_available = shutil.which(self.ffprobe_binary) is not None
        for asset_id in job.input.reference_asset_ids:
            asset = self.assets.get(asset_id)
            check = {"assetId": asset_id, "exists": asset is not None, "ready": bool(asset and asset.status is AssetStatus.READY), "checksum": bool(asset and asset.sha256)}
            if asset and asset.type is AssetType.VIDEO:
                check["ffprobe"] = False
                if ffprobe_available:
                    probe = subprocess.run([self.ffprobe_binary, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", asset.path], check=False, capture_output=True)
                    check["ffprobe"] = probe.returncode == 0
                    if probe.returncode != 0:
                        check["error"] = probe.stderr.decode("utf-8", errors="replace")[-1000:]
                else:
                    check["error"] = "FFprobe executable was not found"
            checks.append(check)
        passed = bool(checks) and all(c.get("exists") and c.get("ready") and c.get("checksum") and c.get("ffprobe", True) for c in checks)
        score = round(100 * sum(1 for c in checks if c.get("exists") and c.get("ready") and c.get("checksum") and c.get("ffprobe", True)) / max(len(checks), 1), 2)
        report = {"jobId": job.id, "stage": "FINAL_QC", "passed": passed, "checks": checks, "score": score}
        payload = (json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        result = self._document(job, AssetType.DOCUMENT, "application/json; charset=utf-8", payload) if passed else None
        if not passed:
            return JobExecutionResult(False, error_code="FINAL_QC_FAILED", error_message=";".join(c.get("error", "INVALID_MEDIA") for c in checks if not (c.get("exists") and c.get("ready") and c.get("checksum") and c.get("ffprobe", True))))
        return result

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False


class tempfile_directory:
    def __enter__(self) -> Path:
        import tempfile
        self._ctx = tempfile.TemporaryDirectory(prefix="aicf-media-")
        return Path(self._ctx.__enter__())

    def __exit__(self, exc_type, exc, tb):
        return self._ctx.__exit__(exc_type, exc, tb)
