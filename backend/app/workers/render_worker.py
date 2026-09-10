from __future__ import annotations

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
    """Render real timeline media with FFmpeg and validate the result with ffprobe."""

    worker_type = "render"

    def __init__(
        self,
        storage: LocalAssetStorage,
        assets: AssetRepository,
        ffmpeg_binary: str = "ffmpeg",
        ffprobe_binary: str = "ffprobe",
    ) -> None:
        self.storage = storage
        self.assets = assets
        self.ffmpeg_binary = ffmpeg_binary
        self.ffprobe_binary = ffprobe_binary
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = shutil.which(self.ffmpeg_binary) is not None and shutil.which(self.ffprobe_binary) is not None

    def health_check(self) -> bool:
        return self._initialized

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="FFMPEG_NOT_AVAILABLE", error_message="FFmpeg/ffprobe executable was not found")
        if not job.input.reference_asset_ids:
            return JobExecutionResult(False, error_code="RENDER_NO_TIMELINE", error_message="No timeline asset supplied")

        timeline_asset = self.assets.get(job.input.reference_asset_ids[0])
        if timeline_asset is None or timeline_asset.type is not AssetType.DOCUMENT:
            return JobExecutionResult(False, error_code="RENDER_TIMELINE_NOT_FOUND", error_message="Timeline document was not found")
        try:
            manifest = json.loads(self.storage.read_bytes(timeline_asset.sha256))
            duration_us = int(manifest["durationUs"])
            tracks = manifest.get("tracks", [])
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            return JobExecutionResult(False, error_code="RENDER_INVALID_TIMELINE", error_message=str(exc))
        if duration_us <= 0 or not tracks:
            return JobExecutionResult(False, error_code="RENDER_EMPTY_TIMELINE", error_message="Timeline has no tracks")

        width, height = self._resolution(job.input.parameters)
        fps = max(1, int(job.input.parameters.get("fps", 30)))
        duration = duration_us / 1_000_000
        timeout = int(job.input.parameters.get("timeoutSeconds", 600))
        subtitles = str(job.input.parameters.get("subtitlePath", "")).strip() or None

        with tempfile.TemporaryDirectory(prefix="aicf-render-") as temp_dir:
            root = Path(temp_dir)
            video_parts: list[Path] = []
            audio_parts: list[Path] = []
            try:
                for track in tracks:
                    track_type = str(track.get("type", "VIDEO")).upper()
                    for clip in track.get("clips", []):
                        asset = self.assets.get(str(clip.get("assetId", "")))
                        if asset is None or asset.status is not AssetStatus.READY:
                            return JobExecutionResult(False, error_code="RENDER_ASSET_NOT_READY", error_message=str(clip.get("assetId")))
                        payload = self.storage.read_bytes(asset.sha256)
                        source = root / f"source-{len(video_parts) + len(audio_parts)}{self._extension(asset.mime_type)}"
                        source.write_bytes(payload)
                        start = max(0.0, int(clip.get("sourceStartUs", 0)) / 1_000_000)
                        clip_duration = max(0.001, int(clip.get("durationUs", 0)) / 1_000_000)
                        if track_type in {"VIDEO", "IMAGE"} or asset.type in {AssetType.VIDEO, AssetType.IMAGE}:
                            part = root / f"video-{len(video_parts):04d}.mp4"
                            if asset.type is AssetType.IMAGE:
                                command = [self.ffmpeg_binary, "-hide_banner", "-loglevel", "error", "-y", "-loop", "1", "-i", str(source), "-t", f"{clip_duration:.6f}", "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2", "-r", str(fps), "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(part)]
                            else:
                                command = [self.ffmpeg_binary, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.6f}", "-i", str(source), "-t", f"{clip_duration:.6f}", "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2", "-r", str(fps), "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(part)]
                            result = self._run(command, timeout)
                            if result is not None:
                                return result
                            video_parts.append(part)
                        elif asset.type is AssetType.AUDIO or track_type in {"AUDIO", "DIALOGUE", "MUSIC", "SFX"}:
                            part = root / f"audio-{len(audio_parts):04d}.m4a"
                            command = [self.ffmpeg_binary, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.6f}", "-i", str(source), "-t", f"{clip_duration:.6f}", "-vn", "-c:a", "aac", "-ar", "48000", "-ac", "2", str(part)]
                            result = self._run(command, timeout)
                            if result is not None:
                                return result
                            audio_parts.append(part)

                if not video_parts:
                    return JobExecutionResult(False, error_code="RENDER_NO_VIDEO", error_message="Timeline contains no video or image clips")

                concat = root / "concat.txt"
                concat.write_text("".join(f"file '{p.as_posix().replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}'\n" for p in video_parts), encoding="utf-8")
                silent_video = root / "video.mp4"
                result = self._run([self.ffmpeg_binary, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(silent_video)], timeout)
                if result is not None:
                    return result

                final = root / f"render-{uuid.uuid4().hex}.mp4"
                command = [self.ffmpeg_binary, "-hide_banner", "-loglevel", "error", "-y", "-i", str(silent_video)]
                if audio_parts:
                    for part in audio_parts:
                        command += ["-i", str(part)]
                    inputs = ";".join(f"[{i}:a]" for i in range(1, len(audio_parts) + 1))
                    command += ["-filter_complex", f"{inputs}amix=inputs={len(audio_parts)}:duration=longest:dropout_transition=2[aout]", "-map", "0:v:0", "-map", "[aout]", "-shortest"]
                else:
                    command += ["-an"]
                if subtitles:
                    command += ["-vf", f"subtitles={subtitles.replace(chr(39), chr(39)+chr(92)+chr(39)+chr(39))}"]
                command += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", str(final)]
                result = self._run(command, timeout)
                if result is not None:
                    return result

                probe = self._probe(final, timeout)
                if isinstance(probe, JobExecutionResult):
                    return probe
                validation = self._validate_probe(probe, width, height, fps)
                if validation:
                    return JobExecutionResult(False, error_code="FINAL_QC_FAILED", error_message=";".join(validation), retryable=False)
                payload = final.read_bytes()
            except OSError as exc:
                return JobExecutionResult(False, error_code="RENDER_IO_ERROR", error_message=str(exc), retryable=True)

        digest, path, size = self.storage.put_bytes(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"render:{job.id}:{digest}"))
        asset = Asset(id=asset_id, project_id=job.project_id, type=AssetType.VIDEO, path=path, mime_type="video/mp4", size_bytes=size, sha256=digest, status=AssetStatus.READY, provenance=build_provenance(job, source_asset_ids=[timeline_asset.id], metadata={"width": width, "height": height, "fps": fps, "durationUs": duration_us, "engine": "ffmpeg", "finalQc": "passed"}, license_status=LicenseStatus.VERIFIED))
        self.assets.create(asset)
        return JobExecutionResult(True, [asset_id], {"width": width, "height": height, "fps": fps, "durationUs": duration_us, "finalQc": "passed"}, f"ffmpeg-{job.id}")

    def _run(self, command: list[str], timeout: int) -> JobExecutionResult | None:
        try:
            completed = subprocess.run(command, check=False, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            return JobExecutionResult(False, error_code="RENDER_TIMEOUT", error_message=str(exc), retryable=True)
        except OSError as exc:
            return JobExecutionResult(False, error_code="RENDER_PROCESS_ERROR", error_message=str(exc), retryable=True)
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace")[-3000:]
            return JobExecutionResult(False, error_code="FFMPEG_RENDER_FAILED", error_message=detail or "FFmpeg failed", retryable=True)
        return None

    def _probe(self, path: Path, timeout: int) -> dict[str, object] | JobExecutionResult:
        try:
            completed = subprocess.run([self.ffprobe_binary, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)], check=False, capture_output=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return JobExecutionResult(False, error_code="FFPROBE_FAILED", error_message=str(exc), retryable=True)
        if completed.returncode != 0:
            return JobExecutionResult(False, error_code="FFPROBE_FAILED", error_message=completed.stderr.decode("utf-8", errors="replace")[-2000:], retryable=False)
        try:
            return json.loads(completed.stdout.decode("utf-8"))
        except json.JSONDecodeError as exc:
            return JobExecutionResult(False, error_code="FFPROBE_INVALID_JSON", error_message=str(exc), retryable=False)

    @staticmethod
    def _validate_probe(probe: dict[str, object], width: int, height: int, fps: int) -> list[str]:
        errors: list[str] = []
        streams = probe.get("streams", [])
        if not isinstance(streams, list) or not streams:
            return ["NO_MEDIA_STREAMS"]
        video = next((s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"), None)
        if not video:
            errors.append("NO_VIDEO_STREAM")
        else:
            if int(video.get("width", 0)) != width or int(video.get("height", 0)) != height:
                errors.append("VIDEO_RESOLUTION_MISMATCH")
        duration = float((probe.get("format") or {}).get("duration", 0)) if isinstance(probe.get("format"), dict) else 0.0
        if duration <= 0:
            errors.append("VIDEO_DURATION_INVALID")
        return errors

    @staticmethod
    def _extension(mime_type: str) -> str:
        return {"image/png": ".png", "image/jpeg": ".jpg", "video/mp4": ".mp4", "audio/mpeg": ".mp3", "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/mp4": ".m4a"}.get(mime_type.split(";")[0].lower(), ".bin")

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
