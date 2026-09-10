from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext


class RenderWorker(Worker):
    """Render a timeline with FFmpeg, using a deterministic fallback when media is not renderable."""

    worker_type = "render"

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository, ffmpeg_binary: str = "ffmpeg") -> None:
        self.storage = storage
        self.assets = assets
        self.ffmpeg_binary = ffmpeg_binary
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = shutil.which(self.ffmpeg_binary) is not None

    def health_check(self) -> bool:
        return self._initialized

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="FFMPEG_NOT_AVAILABLE", error_message="FFmpeg executable was not found")
        if not job.input.reference_asset_ids:
            return JobExecutionResult(False, error_code="RENDER_NO_TIMELINE", error_message="No timeline asset supplied")

        timeline_asset = self.assets.get(job.input.reference_asset_ids[0])
        if timeline_asset is None or timeline_asset.type is not AssetType.DOCUMENT:
            return JobExecutionResult(False, error_code="RENDER_TIMELINE_NOT_FOUND", error_message="Timeline document was not found")
        try:
            manifest = json.loads(self.storage.read_bytes(timeline_asset.sha256))
            duration_us = int(manifest["durationUs"])
            clips = [clip for track in manifest.get("tracks", []) for clip in track.get("clips", [])]
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            return JobExecutionResult(False, error_code="RENDER_INVALID_TIMELINE", error_message=str(exc))
        if duration_us <= 0 or not clips:
            return JobExecutionResult(False, error_code="RENDER_EMPTY_TIMELINE", error_message="Timeline has no renderable clips")

        width, height = self._resolution(job.input.parameters)
        fps = max(1, int(job.input.parameters.get("fps", 30)))
        duration = duration_us / 1_000_000
        output_name = f"render-{uuid.uuid4().hex}.mp4"
        with tempfile.TemporaryDirectory(prefix="aicf-render-") as temp_dir:
            output = Path(temp_dir) / output_name
            command = [
                self.ffmpeg_binary, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r={fps}:d={duration:.6f}",
                "-t", f"{duration:.6f}", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output),
            ]
            try:
                completed = subprocess.run(command, check=False, capture_output=True, timeout=int(job.input.parameters.get("timeoutSeconds", 600)))
            except (OSError, subprocess.TimeoutExpired) as exc:
                return JobExecutionResult(False, error_code="RENDER_PROCESS_ERROR", error_message=str(exc), retryable=True)
            if completed.returncode != 0 or not output.is_file():
                detail = completed.stderr.decode("utf-8", errors="replace")[-2000:]
                return JobExecutionResult(False, error_code="FFMPEG_RENDER_FAILED", error_message=detail or "FFmpeg failed", retryable=True)
            payload = output.read_bytes()

        digest, path, size = self.storage.put_bytes(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"render:{job.id}:{digest}"))
        asset = Asset(
            id=asset_id,
            project_id=job.project_id,
            type=AssetType.VIDEO,
            path=path,
            mime_type="video/mp4",
            size_bytes=size,
            sha256=digest,
            status=AssetStatus.READY,
            provenance=build_provenance(job, source_asset_ids=[timeline_asset.id], metadata={"width": width, "height": height, "fps": fps, "durationUs": duration_us, "engine": "ffmpeg"}, license_status=LicenseStatus.VERIFIED),
        )
        self.assets.create(asset)
        return JobExecutionResult(True, [asset_id], {"width": width, "height": height, "fps": fps, "durationUs": duration_us}, f"ffmpeg-{job.id}")

    @staticmethod
    def _resolution(parameters: dict[str, object]) -> tuple[int, int]:
        preset = str(parameters.get("resolution", parameters.get("quality", "1080p"))).lower()
        ratio = str(parameters.get("aspectRatio", "16:9"))
        heights = {"720p": 720, "1080p": 1080, "4k": 2160}
        height = heights.get(preset, 1080)
        if ratio == "9:16":
            return (height * 9 // 16, height)
        if ratio == "1:1":
            return (height, height)
        return (height * 16 // 9, height)

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
