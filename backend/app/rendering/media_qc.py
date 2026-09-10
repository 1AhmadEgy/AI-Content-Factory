from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class QcThresholds:
    min_duration_s: float = 0.5
    max_duration_delta_s: float = 0.25
    max_width: int | None = None
    max_height: int | None = None


class FinalMediaQC:
    """Post-render technical gate. A process exit code alone never marks media valid."""

    def __init__(self, ffprobe_bin: str = "ffprobe", ffmpeg_bin: str = "ffmpeg"):
        self.ffprobe_bin = ffprobe_bin
        self.ffmpeg_bin = ffmpeg_bin

    def probe(self, path: str) -> dict[str, Any]:
        p = subprocess.run([self.ffprobe_bin, "-v", "error", "-show_streams", "-show_format", "-of", "json", path], capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(p.stderr.strip() or "FFPROBE_FAILED")
        return json.loads(p.stdout)

    def run(self, path: str, expected_duration_s: float | None = None, thresholds: QcThresholds | None = None) -> dict[str, Any]:
        thresholds = thresholds or QcThresholds()
        errors: list[str] = []
        warnings: list[str] = []
        file_path = Path(path)
        if not file_path.is_file() or file_path.stat().st_size == 0:
            return {"passed": False, "errors": ["OUTPUT_MISSING_OR_EMPTY"], "warnings": []}
        try:
            report = self.probe(path)
        except Exception as exc:
            return {"passed": False, "errors": [str(exc)], "warnings": []}
        streams = report.get("streams", [])
        fmt = report.get("format", {})
        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
        duration = float(fmt.get("duration") or 0)
        if duration < thresholds.min_duration_s:
            errors.append("DURATION_TOO_SHORT")
        if expected_duration_s is not None and abs(duration - expected_duration_s) > thresholds.max_duration_delta_s:
            errors.append("DURATION_MISMATCH")
        if not video:
            errors.append("VIDEO_STREAM_MISSING")
        else:
            if thresholds.max_width and int(video.get("width", 0)) > thresholds.max_width:
                errors.append("WIDTH_EXCEEDS_PROFILE")
            if thresholds.max_height and int(video.get("height", 0)) > thresholds.max_height:
                errors.append("HEIGHT_EXCEEDS_PROFILE")
            if video.get("pix_fmt") not in {"yuv420p", "yuvj420p", None}:
                warnings.append(f"UNEXPECTED_PIXEL_FORMAT:{video.get('pix_fmt')}")
        if not audio:
            warnings.append("AUDIO_STREAM_MISSING")
        # Decode the complete file to catch truncation/corruption that metadata alone cannot detect.
        decode = subprocess.run([self.ffmpeg_bin, "-v", "error", "-i", path, "-f", "null", "-"], capture_output=True, text=True)
        if decode.returncode != 0:
            errors.append("DECODE_FAILED")
            if decode.stderr:
                warnings.append(decode.stderr[-1000:])
        return {
            "passed": not errors,
            "errors": errors,
            "warnings": warnings,
            "duration_s": duration,
            "video": video,
            "audio": audio,
            "format": fmt,
        }
