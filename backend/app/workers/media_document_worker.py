from __future__ import annotations

import hashlib
import json
import math
import os
import re
import signal
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from threading import Lock

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext
from ..services.language_media import LanguageMediaService


class MediaDocumentWorker(Worker):
    """Generate subtitles, thumbnails, metadata and final media QC documents."""

    worker_type = "media-document"
    _VTT_CLOCK = re.compile(r"^(?:(\d+):)?(\d{2}):(\d{2})(?:\.(\d{1,3}))?$")

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository, ffmpeg_binary: str = "ffmpeg", ffprobe_binary: str = "ffprobe", subprocess_timeout_seconds: int = 300) -> None:
        self.storage = storage
        self.assets = assets
        self.ffmpeg_binary = ffmpeg_binary
        self.ffprobe_binary = ffprobe_binary
        self.subprocess_timeout_seconds = max(1, int(subprocess_timeout_seconds))
        self._initialized = False
        self._processes: dict[str, subprocess.Popen[str]] = {}
        self._process_lock = Lock()

    def initialize(self) -> None:
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized

    @staticmethod
    def _vtt_time(value: object, default: str) -> str:
        raw = default if value is None else str(value).strip()
        match = MediaDocumentWorker._VTT_CLOCK.fullmatch(raw)
        if not match:
            raise ValueError("INVALID_SUBTITLE_TIME")
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        fraction = match.group(4) or ""
        if minutes >= 60 or seconds >= 60:
            raise ValueError("INVALID_SUBTITLE_TIME")
        milliseconds = int(fraction.ljust(3, "0")) if fraction else 0
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    @classmethod
    def _vtt_seconds(cls, value: str) -> float:
        match = cls._VTT_CLOCK.fullmatch(value)
        if not match:
            raise ValueError("INVALID_SUBTITLE_TIME")
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        fraction = int((match.group(4) or "").ljust(3, "0") or 0)
        return hours * 3600 + minutes * 60 + seconds + fraction / 1000

    @classmethod
    def _subtitle(cls, job: GenerationJob) -> bytes:
        variant = job.input.parameters.get("languagePackVariant")
        language = str(job.input.parameters.get("language") or (variant or {}).get("language") or "") if isinstance(variant, dict) else str(job.input.parameters.get("language") or "")
        cues = LanguageMediaService.subtitle_cues(variant) if isinstance(variant, dict) else []
        if not cues:
            text = str(job.input.parameters.get("text", job.input.parameters.get("narration", ""))).strip()
            if text:
                cues = [{"text": text, "start": 0, "end": job.input.parameters.get("end", "00:00:05.000")}]
        lines = ["WEBVTT", ""]
        output_index = 1
        for cue in cues:
            text = str(cue.get("text", "")).strip()
            if not text:
                continue
            start = cls._vtt_time(cue.get("start", cue.get("startTime")), "00:00:00.000")
            end = cls._vtt_time(cue.get("end", cue.get("endTime")), "00:00:05.000")
            if cls._vtt_seconds(end) <= cls._vtt_seconds(start):
                raise ValueError("INVALID_SUBTITLE_TIMING")
            lines.extend([str(output_index), f"{start} --> {end}", text, ""])
            output_index += 1
        header = f"NOTE language={language}\n\n" if language else ""
        return (header + "\n".join(lines)).encode("utf-8")

    @staticmethod
    def _metadata(job: GenerationJob) -> bytes:
        data = {"projectId": job.project_id, "jobId": job.id, "title": job.input.parameters.get("title", "AI Content"), "description": job.input.parameters.get("description", ""), "tags": job.input.parameters.get("tags", []), "language": job.input.parameters.get("language", "en"), "platforms": job.input.parameters.get("platforms", []), "scheduledAt": job.input.parameters.get("scheduledAt")}
        return (json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")

    def _run_process(self, job_id: str, args: list[str]) -> tuple[subprocess.CompletedProcess[str] | None, bool]:
        proc: subprocess.Popen[str] | None = None
        try:
            # Register the process while holding the same lock used by cancel().
            # This closes the spawn-to-registration window where cancellation
            # could otherwise miss a newly created FFmpeg/FFprobe process.
            with self._process_lock:
                proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
                self._processes[job_id] = proc
            try:
                stdout, stderr = proc.communicate(timeout=self.subprocess_timeout_seconds)
            except subprocess.TimeoutExpired:
                self._terminate_process(proc)
                stdout, stderr = proc.communicate()
                return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr), True
            return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr), False
        except OSError as exc:
            return subprocess.CompletedProcess(args, 127, "", str(exc)), False
        finally:
            with self._process_lock:
                if proc is not None and self._processes.get(job_id) is proc:
                    self._processes.pop(job_id, None)

    @staticmethod
    def _terminate_process(proc: subprocess.Popen[str]) -> None:
        if proc.poll() is not None:
            return
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 1.0
        while proc.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def _thumbnail_asset(self, job: GenerationJob) -> JobExecutionResult:
        source = self.assets.get(job.input.reference_asset_ids[0]) if job.input.reference_asset_ids else None
        if source is None: return JobExecutionResult(False, error_code="THUMBNAIL_SOURCE_NOT_FOUND", error_message="No source asset")
        if source.status is not AssetStatus.READY: return JobExecutionResult(False, error_code="THUMBNAIL_SOURCE_NOT_READY", error_message="Source asset is not ready")
        if source.type is not AssetType.VIDEO: return JobExecutionResult(False, error_code="THUMBNAIL_SOURCE_NOT_VIDEO", error_message="Thumbnail source must be a video")
        source_path = Path(source.path)
        if not source_path.is_file(): return JobExecutionResult(False, error_code="THUMBNAIL_SOURCE_MISSING", error_message=source.path)
        if shutil.which(self.ffmpeg_binary) is None: return JobExecutionResult(False, error_code="FFMPEG_NOT_AVAILABLE", error_message="FFmpeg executable was not found")
        timestamp = str(job.input.parameters.get("timestamp", "00:00:01")).strip()
        try:
            timestamp = self._vtt_time(timestamp, "00:00:01.000")
        except ValueError:
            return JobExecutionResult(False, error_code="THUMBNAIL_TIMESTAMP_INVALID", error_message="Invalid thumbnail timestamp")
        with tempfile.TemporaryDirectory(prefix="aicf-media-") as temp:
            output_path = Path(temp) / "thumbnail.jpg"
            completed, timed_out = self._run_process(job.id, [self.ffmpeg_binary, "-hide_banner", "-loglevel", "error", "-y", "-ss", timestamp, "-i", str(source_path), "-frames:v", "1", "-q:v", "2", str(output_path)])
            if timed_out:
                return JobExecutionResult(False, error_code="THUMBNAIL_TIMEOUT", error_message="FFmpeg thumbnail extraction timed out", retryable=True)
            if completed is None or completed.returncode != 0 or not output_path.is_file():
                error = completed.stderr[-2000:] if completed else "FFmpeg process failed"
                return JobExecutionResult(False, error_code="THUMBNAIL_GENERATION_FAILED", error_message=error, retryable=True)
            digest, path, size = self.storage.put_file(output_path)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"thumbnail:{job.id}:{digest}"))
        self.assets.create(Asset(asset_id, job.project_id, AssetType.THUMBNAIL, path, "image/jpeg", size, digest, AssetStatus.READY, build_provenance(job, source_asset_ids=[source.id], metadata={"engine": "ffmpeg", "timestamp": timestamp}, license_status=LicenseStatus.VERIFIED)))
        return JobExecutionResult(True, [asset_id], {"bytes": size, "format": "jpeg", "timestamp": timestamp}, f"thumbnail-{job.id}")

    def _final_qc(self, job: GenerationJob) -> JobExecutionResult:
        checks = []
        ffprobe_available = shutil.which(self.ffprobe_binary) is not None
        for asset_id in job.input.reference_asset_ids:
            asset = self.assets.get(asset_id)
            check = {"assetId": asset_id, "exists": asset is not None, "ready": bool(asset and asset.status is AssetStatus.READY), "checksum": bool(asset and asset.sha256)}
            if asset and asset.type is AssetType.VIDEO:
                check["ffprobe"] = False
                if ffprobe_available and Path(asset.path).is_file():
                    probe, timed_out = self._run_process(job.id, [self.ffprobe_binary, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", asset.path])
                    if timed_out:
                        check["error"] = "FFprobe timed out"
                    else:
                        check["ffprobe"] = bool(probe and probe.returncode == 0)
                        if probe and probe.returncode != 0: check["error"] = probe.stderr[-1000:]
                elif not ffprobe_available: check["error"] = "FFprobe executable was not found"
                else: check["error"] = "Media file is missing"
            checks.append(check)
        passed = bool(checks) and all(c.get("exists") and c.get("ready") and c.get("checksum") and c.get("ffprobe", True) for c in checks)
        score = round(100 * sum(1 for c in checks if c.get("exists") and c.get("ready") and c.get("checksum") and c.get("ffprobe", True)) / max(len(checks), 1), 2)
        report = {"jobId": job.id, "stage": "FINAL_QC", "passed": passed, "checks": checks, "score": score}
        if not passed:
            return JobExecutionResult(False, error_code="FINAL_QC_FAILED", error_message=";".join(c.get("error", "INVALID_MEDIA") for c in checks if not (c.get("exists") and c.get("ready") and c.get("checksum") and c.get("ffprobe", True))))
        return self._document(job, AssetType.DOCUMENT, "application/json; charset=utf-8", (json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))

    def cancel(self, job_id: str) -> None:
        with self._process_lock:
            proc = self._processes.get(job_id)
        if proc is not None:
            self._terminate_process(proc)

    def shutdown(self) -> None:
        with self._process_lock:
            processes = list(self._processes.values())
        for proc in processes:
            self._terminate_process(proc)
        with self._process_lock:
            self._processes.clear()
        self._initialized = False
