from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..domain.timeline import Timeline, TrackType
from .renderer import RenderProfile, RenderResult, Renderer


@dataclass(frozen=True, slots=True)
class FfmpegRenderOptions:
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    overwrite: bool = False
    subtitles_path: str | None = None
    metadata: Mapping[str, str] | None = None
    crf: int = 20
    preset: str = "medium"
    audio_bitrate: str = "192k"
    timeout_seconds: int = 600


class FfmpegRenderer(Renderer):
    """Canonical FFmpeg renderer used by production workers and pipeline runs."""

    def __init__(self, assets: Mapping[str, str], options: FfmpegRenderOptions | None = None):
        self.assets = dict(assets)
        self.options = options or FfmpegRenderOptions()
        self._processes: dict[str, subprocess.Popen[str]] = {}

    def health_check(self) -> dict[str, object]:
        """Check the media toolchain without allowing a hung executable to block startup."""
        try:
            ffmpeg = subprocess.run(
                [self.options.ffmpeg_bin, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            ffprobe = subprocess.run(
                [self.options.ffprobe_bin, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return {"available": False, "version": None}
        return {
            "available": ffmpeg.returncode == 0 and ffprobe.returncode == 0,
            "version": ffmpeg.stdout.splitlines()[0] if ffmpeg.stdout else None,
        }

    def validate(self, timeline: Timeline, profile: RenderProfile) -> list[str]:
        errors = timeline.validate()
        for track in timeline.tracks:
            for clip in track.clips:
                if clip.asset_id not in self.assets:
                    errors.append(f"ASSET_NOT_FOUND:{clip.asset_id}")
        if profile.width <= 0 or profile.height <= 0:
            errors.append("RENDER_DIMENSIONS_INVALID")
        if profile.fps <= 0:
            errors.append("RENDER_FPS_INVALID")
        if not any(t.type == TrackType.VIDEO and t.clips for t in timeline.tracks):
            errors.append("TIMELINE_HAS_NO_VIDEO")
        return errors

    @staticmethod
    def _is_image(path: str) -> bool:
        return Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

    def _build_args(self, timeline: Timeline, profile: RenderProfile, output: str) -> list[str]:
        video = [t for t in timeline.tracks if t.type == TrackType.VIDEO]
        audio = [t for t in timeline.tracks if t.type in {TrackType.AUDIO, TrackType.DIALOGUE, TrackType.MUSIC, TrackType.SFX}]
        ordered_video = [c for t in video for c in sorted(t.clips, key=lambda c: (c.start_us, c.z_index, c.id))]
        ordered_audio = [c for t in audio for c in sorted(t.clips, key=lambda c: (c.start_us, c.id))]
        inputs = ordered_video + ordered_audio

        args = [self.options.ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y" if self.options.overwrite else "-n"]
        for clip in inputs:
            path = self.assets[clip.asset_id]
            if clip in ordered_video and self._is_image(path):
                args += ["-loop", "1", "-i", path]
            else:
                args += ["-i", path]
        if not inputs:
            raise ValueError("TIMELINE_HAS_NO_MEDIA")

        filter_parts: list[str] = []
        video_labels: list[str] = []
        for index, clip in enumerate(ordered_video):
            start = clip.start_us / 1_000_000
            dur = clip.duration_us / 1_000_000
            source_start = clip.source_start_us / 1_000_000
            label = f"v{index}"
            filter_parts.append(
                f"[{index}:v]trim=start={source_start}:duration={dur},setpts=PTS-STARTPTS+{start}/TB,"
                f"fps={profile.fps:g},scale={profile.width}:{profile.height}:force_original_aspect_ratio=decrease,"
                f"pad={profile.width}:{profile.height}:(ow-iw)/2:(oh-ih)/2:color=black[{label}]"
            )
            video_labels.append(label)

        if video_labels:
            current = video_labels[0]
            for n, label in enumerate(video_labels[1:], 1):
                out = f"ov{n}"
                filter_parts.append(f"[{current}][{label}]overlay=eof_action=pass:shortest=0[{out}]")
                current = out
            final_video = current
            if self.options.subtitles_path:
                subtitle_path = self.options.subtitles_path.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
                filter_parts.append(f"[{final_video}]subtitles='{subtitle_path}'[vsub]")
                final_video = "vsub"
            filter_parts.append(f"[{final_video}]format=yuv420p[vout]")

        audio_labels: list[str] = []
        for offset, clip in enumerate(ordered_audio, start=len(ordered_video)):
            dur = clip.duration_us / 1_000_000
            start = clip.start_us / 1_000_000
            source_start = clip.source_start_us / 1_000_000
            label = f"a{offset}"
            filter_parts.append(
                f"[{offset}:a]atrim=start={source_start}:duration={dur},asetpts=PTS-STARTPTS,"
                f"adelay={int(start * 1000)}:all=1[{label}]"
            )
            audio_labels.append(label)
        if audio_labels:
            joined = "".join(f"[{x}]" for x in audio_labels)
            filter_parts.append(f"{joined}amix=inputs={len(audio_labels)}:duration=longest:dropout_transition=0:normalize=0[aout]")

        args += ["-filter_complex", ";".join(filter_parts)]
        args += ["-map", "[vout]"]
        if audio_labels:
            args += ["-map", "[aout]"]
        args += ["-t", f"{timeline.duration_us / 1_000_000:.6f}", "-r", f"{profile.fps:g}", "-c:v", "libx264", "-preset", self.options.preset, "-crf", str(self.options.crf), "-pix_fmt", "yuv420p"]
        args += ["-c:a", "aac", "-b:a", self.options.audio_bitrate] if audio_labels else ["-an"]
        if self.options.metadata:
            for key, value in sorted(self.options.metadata.items()):
                args += ["-metadata", f"{key}={value}"]
        args += ["-movflags", "+faststart", output]
        return args

    def render(self, timeline: Timeline, profile: RenderProfile, output_path: str) -> RenderResult:
        errors = self.validate(timeline, profile)
        if errors:
            return RenderResult(False, error=";".join(errors))
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkstemp(prefix="acf-render-", suffix=".mp4", dir=destination.parent)[1])
        try:
            args = self._build_args(timeline, profile, str(staging))
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            self._processes[timeline.id] = proc
            try:
                _, stderr = proc.communicate(timeout=max(1, self.options.timeout_seconds))
            except subprocess.TimeoutExpired:
                self.cancel(timeline.id)
                proc.communicate()
                return RenderResult(False, error="FFMPEG_TIMEOUT")
            if proc.returncode != 0:
                return RenderResult(False, error=stderr[-4000:] or "FFMPEG_FAILED")
            os.replace(staging, destination)
            return RenderResult(True, output_path=str(destination))
        except (OSError, ValueError) as exc:
            return RenderResult(False, error=str(exc))
        finally:
            self._processes.pop(timeline.id, None)
            staging.unlink(missing_ok=True)

    def cancel(self, render_id: str) -> bool:
        proc = self._processes.get(render_id)
        if not proc or proc.poll() is not None:
            return False
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return False
        return True

    def probe(self, path: str) -> dict[str, object]:
        completed = subprocess.run([self.options.ffprobe_bin, "-v", "error", "-show_streams", "-show_format", "-of", "json", path], capture_output=True, text=True, timeout=max(1, self.options.timeout_seconds))
        if completed.returncode:
            raise RuntimeError(completed.stderr.strip() or "FFPROBE_FAILED")
        return json.loads(completed.stdout)
