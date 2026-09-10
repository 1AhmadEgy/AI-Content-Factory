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


class FfmpegRenderer(Renderer):
    """Real FFmpeg renderer. Domain code supplies a timeline and immutable asset paths."""

    def __init__(self, assets: Mapping[str, str], options: FfmpegRenderOptions | None = None):
        self.assets = dict(assets)
        self.options = options or FfmpegRenderOptions()
        self._processes: dict[str, subprocess.Popen[str]] = {}

    def health_check(self) -> dict[str, object]:
        result = subprocess.run([self.options.ffmpeg_bin, "-version"], capture_output=True, text=True)
        return {"available": result.returncode == 0, "version": result.stdout.splitlines()[0] if result.stdout else None}

    def validate(self, timeline: Timeline, profile: RenderProfile) -> list[str]:
        errors = timeline.validate()
        for track in timeline.tracks:
            for clip in track.clips:
                if clip.asset_id not in self.assets:
                    errors.append(f"ASSET_NOT_FOUND:{clip.asset_id}")
        if profile.width <= 0 or profile.height <= 0:
            errors.append("RENDER_DIMENSIONS_INVALID")
        return errors

    def _build_args(self, timeline: Timeline, profile: RenderProfile, output: str) -> list[str]:
        video = [t for t in timeline.tracks if t.type == TrackType.VIDEO]
        audio = [t for t in timeline.tracks if t.type in {TrackType.AUDIO, TrackType.DIALOGUE, TrackType.MUSIC, TrackType.SFX}]
        inputs: list[str] = []
        for track in [*video, *audio]:
            for clip in sorted(track.clips, key=lambda c: (c.start_us, c.z_index, c.id)):
                inputs.append(self.assets[clip.asset_id])

        args = [self.options.ffmpeg_bin, "-hide_banner", "-loglevel", "error"]
        if self.options.overwrite:
            args.append("-y")
        else:
            args.append("-n")
        for path in inputs:
            args += ["-i", path]

        if not inputs:
            raise ValueError("TIMELINE_HAS_NO_MEDIA")

        # Deterministic baseline composition: scale/pad each video input and overlay in z-order.
        filter_parts: list[str] = []
        video_labels: list[str] = []
        index = 0
        for track in video:
            for clip in sorted(track.clips, key=lambda c: (c.start_us, c.z_index, c.id)):
                label = f"v{index}"
                start = clip.start_us / 1_000_000
                dur = clip.duration_us / 1_000_000
                filter_parts.append(
                    f"[{index}:v]trim=start={clip.source_start_us/1_000_000}:duration={dur},setpts=PTS-STARTPTS+{start}/TB,"
                    f"scale={profile.width}:{profile.height}:force_original_aspect_ratio=decrease,pad={profile.width}:{profile.height}:(ow-iw)/2:(oh-ih)/2[{label}]"
                )
                video_labels.append(label)
                index += 1
        if video_labels:
            current = video_labels[0]
            for n, label in enumerate(video_labels[1:], 1):
                out = f"ov{n}"
                filter_parts.append(f"[{current}][{label}]overlay=eof_action=pass:shortest=0[{out}]")
                current = out
            filter_parts.append(f"[{current}]format=yuv420p[vout]")

        audio_labels: list[str] = []
        for track in audio:
            for clip in sorted(track.clips, key=lambda c: (c.start_us, c.id)):
                dur = clip.duration_us / 1_000_000
                start = clip.start_us / 1_000_000
                label = f"a{index}"
                filter_parts.append(
                    f"[{index}:a]atrim=start={clip.source_start_us/1_000_000}:duration={dur},asetpts=PTS-STARTPTS,adelay={int(start*1000)}:all=1[{label}]"
                )
                audio_labels.append(label)
                index += 1
        if audio_labels:
            joined = "".join(f"[{x}]" for x in audio_labels)
            filter_parts.append(f"{joined}amix=inputs={len(audio_labels)}:duration=longest:dropout_transition=0:normalize=0[aout]")

        args += ["-filter_complex", ";".join(filter_parts)]
        if video_labels:
            args += ["-map", "[vout]"]
        if audio_labels:
            args += ["-map", "[aout]"]
        args += ["-t", f"{timeline.duration_us/1_000_000:.6f}", "-c:v", "libx264", "-preset", self.options.preset, "-crf", str(self.options.crf), "-pix_fmt", "yuv420p"]
        if audio_labels:
            args += ["-c:a", "aac", "-b:a", self.options.audio_bitrate]
        else:
            args += ["-an"]
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
            _, stderr = proc.communicate()
            if proc.returncode != 0:
                return RenderResult(False, error=stderr[-4000:] or "FFMPEG_FAILED")
            os.replace(staging, destination)
            return RenderResult(True, output_path=str(destination))
        except (OSError, ValueError) as exc:
            return RenderResult(False, error=str(exc))
        finally:
            self._processes.pop(timeline.id, None)
            if staging.exists():
                staging.unlink(missing_ok=True)

    def cancel(self, render_id: str) -> bool:
        proc = self._processes.get(render_id)
        if not proc or proc.poll() is not None:
            return False
        os.killpg(proc.pid, signal.SIGTERM)
        return True

    def probe(self, path: str) -> dict[str, object]:
        completed = subprocess.run([self.options.ffprobe_bin, "-v", "error", "-show_streams", "-show_format", "-of", "json", path], capture_output=True, text=True)
        if completed.returncode:
            raise RuntimeError(completed.stderr.strip() or "FFPROBE_FAILED")
        return json.loads(completed.stdout)
