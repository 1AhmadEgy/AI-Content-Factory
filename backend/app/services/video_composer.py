from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BRAND_CONFIG = ROOT / "app" / "config" / "brands" / "afham_wadhak.json"


class VideoComposer:
    """Small FFmpeg composition facade used by integration tests and workers."""

    def __init__(self, brand_id: str = "afham_wadhak", config_path: str | None = None):
        self.brand_id = brand_id
        self.config_path = Path(config_path) if config_path else DEFAULT_BRAND_CONFIG
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        if self.config.get("id") != brand_id:
            raise ValueError(f"Brand config id mismatch: {self.config.get('id')} != {brand_id}")
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("FFMPEG_NOT_FOUND")

    def _asset(self, relative: str) -> Path:
        return ROOT.parent / relative

    def build_video(self, script_text: str, audio_file: str, output_path: str) -> str:
        """Build a deterministic branded test video: intro + content + outro."""
        if not script_text.strip():
            raise ValueError("script_text must not be empty")

        intro = self._asset(self.config["intro"]["path"])
        outro = self._asset(self.config["outro"]["path"])
        jingle = Path(audio_file)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        for path in (intro, outro, jingle):
            if not path.exists():
                raise FileNotFoundError(path)

        content = output.with_name(output.stem + ".content.mp4")
        merged = output.with_name(output.stem + ".merged.mp4")
        safe_text = script_text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        content_filter = (
            "drawtext="
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{safe_text}':fontcolor=white:fontsize=54:"
            "line_spacing=12:box=1:boxcolor=0x111111@0.85:boxborderw=28:"
            "x=(w-text_w)/2:y=(h-text_h)/2"
        )

        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=0x111111:s=1080x1920:r=30:d=4",
                "-stream_loop", "-1", "-i", str(jingle),
                "-vf", content_filter,
                "-map", "0:v:0", "-map", "1:a:0",
                "-t", "4", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest", "-movflags", "+faststart",
                "-metadata", f"brand={self.brand_id}",
                "-metadata", f"script={script_text}",
                str(content),
            ],
            check=True,
        )

        # Add silent audio to intro/outro so all three segments share A/V streams.
        silent_intro = output.with_name(output.stem + ".intro.mp4")
        silent_outro = output.with_name(output.stem + ".outro.mp4")
        for source, target, duration in ((intro, silent_intro, "2.5"), (outro, silent_outro, "2.5")):
            subprocess.run(
                [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(source), "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                    "-map", "0:v:0", "-map", "1:a:0", "-t", duration,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                    str(target),
                ],
                check=True,
            )

        concat_file = output.with_name(output.stem + ".concat.txt")
        concat_file.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in (silent_intro, content, silent_outro)) + "\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "concat", "-safe", "0", "-i", str(concat_file),
                "-c", "copy", "-movflags", "+faststart", str(merged),
            ],
            check=True,
        )
        shutil.move(merged, output)

        for path in (content, silent_intro, silent_outro, concat_file):
            path.unlink(missing_ok=True)
        return str(output)
