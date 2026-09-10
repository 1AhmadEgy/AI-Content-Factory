from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob, JobType
from ..domain.timeline import Timeline, TimelineClip, TimelineTrack, TrackType
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext
from ..rendering.ffmpeg_renderer import FfmpegRenderOptions, FfmpegRenderer
from ..rendering.renderer import RenderProfile


class RepurposeWorker(Worker):
    """Render provider-neutral vertical clips and thumbnails from an existing video asset."""

    worker_type = "repurpose"

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository) -> None:
        self.storage, self.assets, self._initialized = storage, assets, False
        self._renderers: dict[str, FfmpegRenderer] = {}

    def initialize(self) -> None:
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized and shutil.which(os.getenv("AICF_FFMPEG_BIN", "ffmpeg")) is not None and shutil.which(os.getenv("AICF_FFPROBE_BIN", "ffprobe")) is not None

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        if job.type is not JobType.REPURPOSE:
            return JobExecutionResult(False, error_code="UNSUPPORTED_JOB_TYPE", error_message=job.type.value)
        references = list(dict.fromkeys(job.input.reference_asset_ids))
        source = next((self.assets.get(asset_id) for asset_id in references if self.assets.get(asset_id)), None)
        if source is None or source.status is not AssetStatus.READY:
            return JobExecutionResult(False, error_code="REPURPOSE_SOURCE_NOT_READY", error_message="No ready source asset")
        if source.type is not AssetType.VIDEO:
            return JobExecutionResult(False, error_code="REPURPOSE_SOURCE_NOT_VIDEO", error_message="Repurposing requires a video source")
        if not Path(source.path).is_file():
            return JobExecutionResult(False, error_code="REPURPOSE_SOURCE_MISSING", error_message=source.path)

        platforms = list(dict.fromkeys(str(p).lower().strip() for p in job.input.parameters.get("platforms", ["youtube_shorts", "tiktok", "instagram_reels", "facebook_reels"]) if str(p).strip()))
        if not platforms:
            return JobExecutionResult(False, error_code="REPURPOSE_NO_PLATFORMS", error_message="At least one platform is required")
        duration_seconds = float(job.input.parameters.get("clipDurationSeconds", 60))
        if duration_seconds <= 0:
            return JobExecutionResult(False, error_code="REPURPOSE_DURATION_INVALID", error_message="clipDurationSeconds must be positive")
        duration_us = max(1, int(duration_seconds * 1_000_000))
        source_start_us = max(0, int(job.input.parameters.get("sourceStartUs", 0)))
        profile = RenderProfile(name="vertical_1080p", width=608, height=1080, fps=float(job.input.parameters.get("fps", 30)))
        options = FfmpegRenderOptions(
            ffmpeg_bin=os.getenv("AICF_FFMPEG_BIN", "ffmpeg"),
            ffprobe_bin=os.getenv("AICF_FFPROBE_BIN", "ffprobe"),
            overwrite=True,
            timeout_seconds=max(1, int(job.input.parameters.get("timeoutSeconds", 600))),
        )
        outputs: list[dict[str, object]] = []

        renderer = FfmpegRenderer({source.id: source.path}, options)
        self._renderers[job.id] = renderer
        try:
            health = renderer.health_check()
            if not health.get("available"):
                return JobExecutionResult(False, error_code="FFMPEG_NOT_AVAILABLE", error_message="FFmpeg/FFprobe executable was not found")
            source_probe = renderer.probe(source.path)
            source_duration = float((source_probe.get("format") or {}).get("duration", 0) or 0)
            if source_duration <= source_start_us / 1_000_000:
                return JobExecutionResult(False, error_code="REPURPOSE_SOURCE_OFFSET_INVALID", error_message="sourceStartUs is beyond the source duration")
            effective_duration_us = min(duration_us, max(1, int((source_duration - source_start_us / 1_000_000) * 1_000_000)))

            for index, platform in enumerate(platforms):
                if context:
                    context.report_progress(index / len(platforms), f"repurpose:{platform}:render")
                timeline = Timeline(
                    id=f"repurpose:{job.id}:{platform}",
                    project_id=job.project_id,
                    duration_us=effective_duration_us,
                    tracks=[TimelineTrack(id=f"video:{job.id}:{platform}", type=TrackType.VIDEO, clips=[TimelineClip(id=f"clip:{job.id}:{platform}", asset_id=source.id, start_us=0, duration_us=effective_duration_us, source_start_us=source_start_us)])],
                )
                errors = timeline.validate()
                if errors:
                    return JobExecutionResult(False, error_code="REPURPOSE_TIMELINE_INVALID", error_message=errors[0])
                with tempfile.TemporaryDirectory(prefix="aicf-repurpose-") as temp:
                    output = Path(temp) / f"{platform}.mp4"
                    result = renderer.render(timeline, profile, str(output))
                    if not result.success or not result.output_path:
                        return JobExecutionResult(False, error_code="REPURPOSE_RENDER_FAILED", error_message=result.error or platform, retryable=True)
                    probe = renderer.probe(result.output_path)
                    streams = probe.get("streams", []) if isinstance(probe, dict) else []
                    video_streams = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"]
                    if not video_streams:
                        return JobExecutionResult(False, error_code="REPURPOSE_QC_FAILED", error_message=f"No video stream: {platform}", retryable=True)
                    actual_width = int(video_streams[0].get("width", 0))
                    actual_height = int(video_streams[0].get("height", 0))
                    actual_duration = float((probe.get("format") or {}).get("duration", 0) or 0)
                    expected_duration = effective_duration_us / 1_000_000
                    if (actual_width, actual_height) != (profile.width, profile.height) or abs(actual_duration - expected_duration) > max(0.25, 1.0 / profile.fps * 3):
                        return JobExecutionResult(False, error_code="REPURPOSE_QC_FAILED", error_message=f"Unexpected media output for {platform}: {actual_width}x{actual_height}, {actual_duration:.3f}s", retryable=True)
                    payload = output.read_bytes()
                    thumbnail = Path(temp) / f"{platform}.jpg"
                    try:
                        thumb = subprocess.run([options.ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y", "-ss", "0", "-i", str(output), "-frames:v", "1", "-q:v", "2", str(thumbnail)], check=False, capture_output=True, timeout=options.timeout_seconds)
                    except subprocess.TimeoutExpired:
                        return JobExecutionResult(False, error_code="REPURPOSE_THUMBNAIL_TIMEOUT", error_message=f"Thumbnail extraction timed out: {platform}", retryable=True)
                    if thumb.returncode != 0 or not thumbnail.is_file():
                        return JobExecutionResult(False, error_code="REPURPOSE_THUMBNAIL_FAILED", error_message=thumb.stderr.decode("utf-8", errors="replace")[-2000:], retryable=True)
                    thumbnail_payload = thumbnail.read_bytes()
                digest, path, size = self.storage.put_bytes(payload)
                asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"repurpose-video:{job.id}:{platform}:{digest}"))
                self.assets.create(Asset(asset_id, job.project_id, AssetType.VIDEO, path, "video/mp4", size, AssetStatus.READY, build_provenance(job, source_asset_ids=[source.id], metadata={"platform": platform, "profile": profile.name, "resolution": f"{actual_width}x{actual_height}", "sourceStartUs": source_start_us, "durationUs": effective_duration_us, "durationSeconds": actual_duration, "qc": "passed"}, license_status=LicenseStatus.VERIFIED)))
                thumb_digest, thumb_path, thumb_size = self.storage.put_bytes(thumbnail_payload)
                thumb_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"repurpose-thumbnail:{job.id}:{platform}:{thumb_digest}"))
                self.assets.create(Asset(thumb_id, job.project_id, AssetType.THUMBNAIL, thumb_path, "image/jpeg", thumb_size, AssetStatus.READY, build_provenance(job, source_asset_ids=[asset_id], metadata={"platform": platform, "engine": "ffmpeg", "timestamp": "0"}, license_status=LicenseStatus.VERIFIED)))
                outputs.append({"platform": platform, "assetId": asset_id, "thumbnailAssetId": thumb_id, "sha256": digest, "bytes": size, "resolution": f"{actual_width}x{actual_height}", "durationUs": effective_duration_us, "durationSeconds": actual_duration})

            if context:
                context.report_progress(1.0, "repurpose:complete")
            manifest = {"jobId": job.id, "projectId": job.project_id, "sourceAssetId": source.id, "outputs": outputs}
            manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
            digest, path, size = self.storage.put_bytes(manifest_bytes)
            manifest_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"repurpose-manifest:{job.id}:{digest}"))
            self.assets.create(Asset(manifest_id, job.project_id, AssetType.DOCUMENT, path, "application/json; charset=utf-8", size, digest, AssetStatus.READY, build_provenance(job, source_asset_ids=[source.id] + [str(item["assetId"]) for item in outputs] + [str(item["thumbnailAssetId"]) for item in outputs], metadata={"repurposing": True, "rendered": True, "qc": "passed", "thumbnailCount": len(outputs)}, license_status=LicenseStatus.VERIFIED)))
            return JobExecutionResult(True, [str(item["assetId"]) for item in outputs] + [str(item["thumbnailAssetId"]) for item in outputs] + [manifest_id], {"outputCount": len(outputs), "manifestAssetId": manifest_id}, f"repurpose-{job.id}")
        finally:
            self._renderers.pop(job.id, None)

    def cancel(self, job_id: str) -> None:
        renderer = self._renderers.get(job_id)
        if renderer:
            renderer.cancel_all()

    def shutdown(self) -> None:
        for renderer in list(self._renderers.values()):
            renderer.shutdown()
        self._renderers.clear()
        self._initialized = False
