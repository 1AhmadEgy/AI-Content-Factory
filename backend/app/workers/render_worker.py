from __future__ import annotations

import json
import uuid
from pathlib import Path

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob
from ..domain.timeline import Timeline, TimelineClip, TimelineTrack, TrackType
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext
from ..rendering.ffmpeg_renderer import FfmpegRenderOptions, FfmpegRenderer
from ..rendering.renderer import RenderProfile


class RenderWorker(Worker):
    """Production render worker backed by the canonical FfmpegRenderer."""

    worker_type = "render"

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository, ffmpeg_binary: str = "ffmpeg", ffprobe_binary: str = "ffprobe") -> None:
        self.storage = storage
        self.assets = assets
        self.ffmpeg_binary = ffmpeg_binary
        self.ffprobe_binary = ffprobe_binary
        self._initialized = False
        self._renderers: dict[str, FfmpegRenderer] = {}

    def initialize(self) -> None:
        renderer = FfmpegRenderer({}, FfmpegRenderOptions(ffmpeg_bin=self.ffmpeg_binary, ffprobe_bin=self.ffprobe_binary))
        health = renderer.health_check()
        self._initialized = bool(health.get("available"))

    def health_check(self) -> bool:
        return self._initialized

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        context.report_progress(0.10, "preparing")
        if not self._initialized:
            return JobExecutionResult(False, error_code="FFMPEG_NOT_AVAILABLE", error_message="FFmpeg/ffprobe executable was not found")
        if not job.input.reference_asset_ids:
            return JobExecutionResult(False, error_code="RENDER_NO_TIMELINE", error_message="No timeline asset supplied")

        timeline_asset = self.assets.get(job.input.reference_asset_ids[0])
        if timeline_asset is None or timeline_asset.type is not AssetType.DOCUMENT:
            return JobExecutionResult(False, error_code="RENDER_TIMELINE_NOT_FOUND", error_message="Timeline document was not found")

        try:
            manifest = json.loads(self.storage.read_bytes(timeline_asset.sha256))
            timeline = self._timeline_from_manifest(manifest, job.project_id, job.id)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            return JobExecutionResult(False, error_code="RENDER_INVALID_TIMELINE", error_message=str(exc))
        if not timeline.tracks:
            return JobExecutionResult(False, error_code="RENDER_EMPTY_TIMELINE", error_message="Timeline has no tracks")
        context.report_progress(0.20, "assets_loaded")

        width, height = self._resolution(job.input.parameters)
        fps = max(1, int(job.input.parameters.get("fps", 30)))
        profile = RenderProfile(name=f"{width}x{height}@{fps}", width=width, height=height, fps=float(fps))
        asset_paths: dict[str, str] = {}
        for track in timeline.tracks:
            for clip in track.clips:
                asset = self.assets.get(clip.asset_id)
                if asset is None or asset.status is not AssetStatus.READY:
                    return JobExecutionResult(False, error_code="RENDER_ASSET_NOT_READY", error_message=clip.asset_id)
                path = Path(asset.path)
                if not path.is_file():
                    return JobExecutionResult(False, error_code="RENDER_ASSET_MISSING", error_message=clip.asset_id)
                asset_paths[clip.asset_id] = str(path)

        renderer = FfmpegRenderer(
            asset_paths,
            FfmpegRenderOptions(
                ffmpeg_bin=self.ffmpeg_binary,
                ffprobe_bin=self.ffprobe_binary,
                overwrite=True,
                subtitles_path=str(job.input.parameters.get("subtitlePath", "")).strip() or None,
            ),
        )
        self._renderers[job.id] = renderer
        output = self.storage.root / "staging" / f"render-{job.id}-{uuid.uuid4().hex}.mp4"
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            context.report_progress(0.30, "rendering")
            result = renderer.render(timeline, profile, str(output))
            if not result.success or not result.output_path:
                message = result.error or "FFmpeg render failed"
                return JobExecutionResult(False, error_code="FFMPEG_RENDER_FAILED", error_message=message, retryable=True)
            context.report_progress(0.82, "audio_mix_complete")
            probe = renderer.probe(result.output_path)
            errors = self._validate_probe(probe, width, height)
            if errors:
                return JobExecutionResult(False, error_code="FINAL_QC_FAILED", error_message=";".join(errors), retryable=False)
            context.report_progress(0.90, "ffprobe_qc_passed")
            payload = Path(result.output_path).read_bytes()
        except (OSError, RuntimeError, ValueError) as exc:
            return JobExecutionResult(False, error_code="RENDER_IO_ERROR", error_message=str(exc), retryable=True)
        finally:
            self._renderers.pop(job.id, None)
            output.unlink(missing_ok=True)

        context.report_progress(0.96, "provenance")
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
            provenance=build_provenance(job, source_asset_ids=[timeline_asset.id, *asset_paths.keys()], metadata={"width": width, "height": height, "fps": fps, "durationUs": timeline.duration_us, "engine": "ffmpeg", "finalQc": "passed"}, license_status=LicenseStatus.VERIFIED),
        )
        self.assets.create(asset)
        return JobExecutionResult(True, [asset_id], {"width": width, "height": height, "fps": fps, "durationUs": timeline.duration_us, "finalQc": "passed", "engine": "ffmpeg"}, f"ffmpeg-{job.id}")

    @staticmethod
    def _timeline_from_manifest(manifest: dict[str, object], project_id: str, timeline_id: str) -> Timeline:
        tracks: list[TimelineTrack] = []
        for raw_track in manifest.get("tracks", []):
            if not isinstance(raw_track, dict):
                continue
            track_type = TrackType(str(raw_track.get("type", "VIDEO")).upper())
            clips: list[TimelineClip] = []
            for raw_clip in raw_track.get("clips", []):
                if not isinstance(raw_clip, dict):
                    continue
                clips.append(TimelineClip(id=str(raw_clip.get("id", uuid.uuid4().hex)), asset_id=str(raw_clip["assetId"]), start_us=int(raw_clip.get("startUs", 0)), duration_us=int(raw_clip.get("durationUs", 0)), source_start_us=int(raw_clip.get("sourceStartUs", 0)), z_index=int(raw_clip.get("zIndex", 0))))
            tracks.append(TimelineTrack(id=str(raw_track.get("id", uuid.uuid4().hex)), type=track_type, clips=clips))
        return Timeline(id=timeline_id, project_id=project_id, duration_us=int(manifest["durationUs"]), timebase=int(manifest.get("timebase", 1_000_000)), tracks=tracks)

    @staticmethod
    def _validate_probe(probe: dict[str, object], width: int, height: int) -> list[str]:
        streams = probe.get("streams", [])
        if not isinstance(streams, list) or not streams:
            return ["NO_MEDIA_STREAMS"]
        video = next((s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"), None)
        if not video:
            return ["NO_VIDEO_STREAM"]
        errors: list[str] = []
        if int(video.get("width", 0)) != width or int(video.get("height", 0)) != height:
            errors.append("VIDEO_RESOLUTION_MISMATCH")
        media_duration = probe.get("format", {})
        duration = float(media_duration.get("duration", 0)) if isinstance(media_duration, dict) else 0.0
        if duration <= 0:
            errors.append("VIDEO_DURATION_INVALID")
        return errors

    @staticmethod
    def _resolution(parameters: dict[str, object]) -> tuple[int, int]:
        preset = str(parameters.get("resolution", parameters.get("quality", "1080p"))).lower()
        ratio = str(parameters.get("aspectRatio", "16:9"))
        height = {"720p": 720, "1080p": 1080, "4k": 2160}.get(preset, 1080)
        if ratio == "9:16":
            return (height * 9 // 16, height)
        if ratio == "1:1":
            return (height, height)
        return (height * 16 // 9, height)

    def cancel(self, job_id: str) -> None:
        renderer = self._renderers.get(job_id)
        if renderer is not None:
            renderer.cancel(job_id)

    def shutdown(self) -> None:
        for renderer in list(self._renderers.values()):
            for render_id in list(renderer._processes):
                renderer.cancel(render_id)
        self._renderers.clear()
        self._initialized = False
