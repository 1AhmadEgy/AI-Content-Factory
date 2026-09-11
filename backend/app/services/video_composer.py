from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BRANDS_DIR = ROOT / "backend" / "app" / "config" / "brands"


class VideoComposer:
    """FFmpeg composition facade for brand-driven vertical videos."""

    def __init__(self, brand_id: str = "afham_wadhak", config_path: str | None = None):
        self.brand_id = brand_id
        self.config_path = Path(config_path) if config_path else BRANDS_DIR / f"{brand_id}.json"
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        configured_id = self.config.get("brand_id") or self.config.get("id")
        if configured_id != brand_id:
            raise ValueError(f"Brand config id mismatch: {configured_id} != {brand_id}")
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("FFMPEG_NOT_FOUND")

    def _asset(self, relative: str) -> Path:
        return ROOT / relative

    def _brand_asset(self, filename: str) -> Path:
        folder = self.config.get("file_structure", {}).get("brand_folder", f"assets/branding/{self.brand_id}/")
        return self._asset(str(Path(folder) / filename))

    def build_video(self, script_text: str, audio_file: str, output_path: str) -> str:
        """Build intro + branded content + outro as a deterministic MP4."""
        if not script_text.strip():
            raise ValueError("script_text must not be empty")

        intro = self._brand_asset("intro.mp4")
        outro = self._brand_asset("outro.mp4")
        watermark = self._brand_asset("watermark.png")
        jingle = Path(audio_file)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        for path in (intro, outro, watermark, jingle):
            if not path.exists():
                raise FileNotFoundError(path)

        content = output.with_name(output.stem + ".content.mp4")
        merged = output.with_name(output.stem + ".merged.mp4")
        safe_text = script_text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        opacity = float(self.config.get("watermark", {}).get("opacity", 0.35))
        opacity = max(0.0, min(1.0, opacity))
        content_filter = (
            "drawtext="
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{safe_text}':fontcolor=white:fontsize=54:"
            "line_spacing=12:box=1:boxcolor=0x111111@0.85:boxborderw=28:"
            "x=(w-text_w)/2:y=(h-text_h)/2,"
            f"movie='{watermark.as_posix()}'[wm];[in][wm]"
            f"format=rgba,colorchannelmixer=aa={opacity}[wm2];[in][wm2]"
            "overlay=W-w-36:H-h-36[out]"
        )

        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=0x111111:s=1080x1920:r=30:d=4",
                "-stream_loop", "-1", "-i", str(jingle),
                "-i", str(watermark),
                "-filter_complex",
                (
                    "[0:v]drawtext="
                    "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
                    f"text='{safe_text}':fontcolor=white:fontsize=54:"
                    "line_spacing=12:box=1:boxcolor=0x111111@0.85:boxborderw=28:"
                    "x=(w-text_w)/2:y=(h-text_h)/2[txt];"
                    f"[2:v]format=rgba,colorchannelmixer=aa={opacity}[wm];"
                    "[txt][wm]overlay=W-w-36:H-h-36[v]"
                ),
                "-map", "[v]", "-map", "1:a:0", "-t", "4", "-r", "30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-shortest", "-movflags", "+faststart",
                "-metadata", f"brand_id={self.brand_id}",
                "-metadata", f"brand_name={self.config.get('brand_name_en', self.brand_id)}",
                str(content),
            ],
            check=True,
        )

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
