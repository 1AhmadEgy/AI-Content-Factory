from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class SubtitleCue:
    start_ms: int
    end_ms: int
    text: str


def write_srt(cues: list[SubtitleCue], output: str) -> str:
    def stamp(ms: int) -> str:
        ms = max(0, ms)
        h, rem = divmod(ms, 3_600_000)
        m, rem = divmod(rem, 60_000)
        s, milli = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"
    lines: list[str] = []
    for i, cue in enumerate(cues, 1):
        if cue.end_ms <= cue.start_ms:
            raise ValueError(f"INVALID_SUBTITLE_RANGE:{i}")
        text = cue.text.replace("\r", "").replace("\n", " ").strip()
        lines += [str(i), f"{stamp(cue.start_ms)} --> {stamp(cue.end_ms)}", text, ""]
    Path(output).write_text("\n".join(lines), encoding="utf-8")
    return output


def extract_thumbnail(
    video: str,
    output: str,
    at_s: float = 0.0,
    ffmpeg_bin: str = "ffmpeg",
    timeout_seconds: float = 60.0,
) -> str:
    """Extract one thumbnail without allowing FFmpeg to block indefinitely."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        str(max(0.0, at_s)),
        "-i",
        video,
        "-frames:v",
        "1",
        "-q:v",
        "2",
        output,
    ]
    try:
        process = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("THUMBNAIL_TIMEOUT") from exc
    if process.returncode or not output_path.is_file() or output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(process.stderr.strip() or "THUMBNAIL_GENERATION_FAILED")
    return output


def write_metadata_sidecar(output: str, metadata: Mapping[str, str]) -> str:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(metadata.items())), ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_provenance_manifest(output: str, *, timeline_id: str, timeline_version: str, render_profile: str, renderer: str, renderer_version: str, source_assets: Mapping[str, str], qc: Mapping[str, object]) -> str:
    payload = {
        "artifact": {"path": output, "sha256": sha256_file(output)},
        "timeline": {"id": timeline_id, "version": timeline_version},
        "renderProfile": render_profile,
        "renderer": renderer,
        "rendererVersion": renderer_version,
        "sourceAssets": dict(sorted(source_assets.items())),
        "qc": dict(qc),
    }
    sidecar = str(Path(output).with_suffix(Path(output).suffix + ".provenance.json"))
    Path(sidecar).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return sidecar
