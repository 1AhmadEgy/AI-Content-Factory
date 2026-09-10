from __future__ import annotations

import json
import shutil
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
    """Render provider-neutral vertical clips from an existing video asset."""

    worker_type = "repurpose"

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository) -> None:
        self.storage, self.assets, self._initialized = storage, assets, False
        self._renderers: dict[str, FfmpegRenderer] = {}

    def initialize(self) -> None:
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized and shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        if job.type is not JobType.REPURPOSE:
            return JobExecutionResult(False, error_code="UNSUPPORTED_JOB_TYPE", error_message=job.type.value)
        source = next((self.assets.get(asset_id) for asset_id in job.input.reference_asset_ids if self.assets.get(asset_id)), None)
        if source is None or source.status is not AssetStatus.READY:
            return JobExecutionResult(False, error_code="REPURPOSE_SOURCE_NOT_READY", error_message="No ready source asset")
        if source.type is not AssetType.VIDEO:
            return JobExecutionResult(False, error_code="REPURPOSE_SOURCE_NOT_VIDEO", error_message="Repurposing requires a video source")
        if not Path(source.path).is_file():
            return JobExecutionResult(False, error_code="REPURPOSE_SOURCE_MISSING", error_message=source.path)

        platforms = [str(p).lower() for p in job.input.parameters.get("platforms", ["youtube_shorts", "tiktok", "instagram_reels", "facebook_reels"])]
        duration_us = max(1, int(float(job.input.parameters.get("clipDurationSeconds", 60)) * 1_000_000))
        source_start_us = max(0, int(job.input.parameters.get("sourceStartUs", 0)))
        profile = RenderProfile(name="vertical_1080p", width=608, height=1080, fps=float(job.input.parameters.get("fps", 30)))
        outputs: list[dict[str, object]] = []

        renderer = FfmpegRenderer({source.id: source.path}, FfmpegRenderOptions(overwrite=True, timeout_seconds=int(job.input.parameters.get("timeoutSeconds", 600))))
        self._renderers[job.id] = renderer
        try:
            health = renderer.health_check()
            if not health.get("available"):
                return JobExecutionResult(False, error_code="FFMPEG_NOT_AVAILABLE", error_message="FFmpeg/FFprobe executable was not found")
            for index, platform in enumerate(platforms):
                if context:
                    context.report_progress(index / max(len(platforms), 1), f"repurpose:{platform}:render")
                timeline = Timeline(
                    id=f"repurpose:{job.id}:{platform}",
                    project_id=job.project_id,
                    duration_us=duration_us,
                    tracks=[TimelineTrack(
                        id=f"video:{job.id}:{platform}",
                        type=TrackType.VIDEO,
                        clips=[TimelineClip(
                            id=f"clip:{job.id}:{platform}",
                            asset_id=source.id,
                            start_us=0,
                            duration_us=duration_us,
                            source_start_us=source_start_us,
                        )],
                    )],
                )
                errors = timeline.validate()
                if errors:
                    return JobExecutionResult(False, error_code="REPURPOSE_TIMELINE_INVALID", error_message=errors[0])
                with tempfile.TemporaryDirectory(prefix="aicf-repurpose-") as temp:
                    output = Path(temp) / f"{platform}.mp4"
                    result = renderer.render(timeline, profile, str(output))
                    if not result.success or not result.output_path:
                        return JobExecutionResult(False, error_code="REPURPOSE_RENDER_FAILED", error_message=result.error or platform, retryable=True)
                    payload = Path(result.output_path).read_bytes()
                digest, path, size = self.storage.put_bytes(payload)
                asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"repurpose-video:{job.id}:{platform}:{digest}"))
                self.assets.create(Asset(
                    asset_id, job.project_id, AssetType.VIDEO, path, "video/mp4", size, digest, AssetStatus.READY,
                    build_provenance(job, source_asset_ids=[source.id], metadata={"platform": platform, "profile": profile.name, "resolution": "608x1080", "sourceStartUs": source_start_us, "durationUs": duration_us}, license_status=LicenseStatus.VERIFIED),
                ))
                outputs.append({"platform": platform, "assetId": asset_id, "sha256": digest, "bytes": size, "resolution": "608x1080", "durationUs": duration_us})

            if context:
                context.report_progress(1.0, "repurpose:complete")
            manifest = {"jobId": job.id, "projectId": job.project_id, "sourceAssetId": source.id, "outputs": outputs}
            manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
            digest, path, size = self.storage.put_bytes(manifest_bytes)
            manifest_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"repurpose-manifest:{job.id}:{digest}"))
            self.assets.create(Asset(
                manifest_id, job.project_id, AssetType.DOCUMENT, path, "application/json; charset=utf-8", size, digest, AssetStatus.READY,
                build_provenance(job, source_asset_ids=[source.id] + [str(item["assetId"]) for item in outputs], metadata={"repurposing": True, "rendered": True}, license_status=LicenseStatus.VERIFIED),
            ))
            return JobExecutionResult(True, [str(item["assetId"]) for item in outputs] + [manifest_id], {"outputCount": len(outputs), "manifestAssetId": manifest_id}, f"repurpose-{job.id}")
        finally:
            self._renderers.pop(job.id, None)

    def cancel(self, job_id: str) -> None:
        renderer = self._renderers.get(job_id)
        if renderer:
            renderer.cancel(f"repurpose:{job_id}:youtube_shorts")
            renderer.cancel(f"repurpose:{job_id}:tiktok")
            renderer.cancel(f"repurpose:{job_id}:instagram_reels")
            renderer.cancel(f"repurpose:{job_id}:facebook_reels")

    def shutdown(self) -> None:
        for renderer in list(self._renderers.values()):
            for render_id in list(renderer._processes):
                renderer.cancel(render_id)
        self._renderers.clear()
        self._initialized = False
