from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BRANDS_DIR = ROOT / "backend" / "app" / "config" / "brands"


class VideoComposer:
    """FFmpeg composition facade that never invents audio tracks."""

    def __init__(self, brand_id: str = "afham_wadhak", config_path: str | None = None):
        self.brand_id = brand_id
        self.config_path = Path(config_path) if config_path else BRANDS_DIR / f"{brand_id}.json"
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        configured_id = self.config.get("brand_id") or self.config.get("id")
        if configured_id != brand_id:
            raise ValueError(f"Brand config id mismatch: {configured_id} != {brand_id}")
        self.ffmpeg_bin = os.getenv("AICF_FFMPEG_BIN", "ffmpeg")
        if shutil.which(self.ffmpeg_bin) is None:
            raise RuntimeError("FFMPEG_NOT_FOUND")

    def _asset(self, relative: str) -> Path:
        return ROOT / relative

    def _brand_asset(self, filename: str) -> Path:
        folder = self.config.get("file_structure", {}).get("brand_folder", f"assets/branding/{self.brand_id}/")
        return self._asset(str(Path(folder) / filename))

    def _has_audio(self, source: Path) -> bool:
        ffprobe = os.getenv("AICF_FFPROBE_BIN", "ffprobe")
        if shutil.which(ffprobe) is None:
            raise RuntimeError("FFPROBE_NOT_FOUND")
        result = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=index", "-of", "csv=p=0", str(source)],
            capture_output=True,
            text=True,
            check=False,
        )
        return bool(result.stdout.strip())

    def build_video(self, script_text: str, audio_file: str, output_path: str) -> str:
        if not script_text.strip():
            raise ValueError("SCRIPT_TEXT_REQUIRED")

        intro = self._brand_asset("intro.mp4")
        outro = self._brand_asset("outro.mp4")
        watermark = self._brand_asset("watermark.png")
        jingle = Path(audio_file)
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        for path in (intro, outro, watermark, jingle):
            if not path.is_file() or path.stat().st_size == 0:
                raise FileNotFoundError(f"BRAND_ASSET_NOT_FOUND:{path}")
        if not self._has_audio(jingle):
            raise ValueError("REAL_AUDIO_TRACK_REQUIRED")

        content = output.with_name(output.stem + ".content.mp4")
        merged = output.with_name(output.stem + ".merged.mp4")
        safe_text = script_text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        opacity = max(0.0, min(1.0, float(self.config.get("watermark", {}).get("opacity", 0.35))))

        subprocess.run(
            [
                self.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=0x111111:s=1080x1920:r=30:d=4",
                "-stream_loop", "-1", "-i", str(jingle), "-i", str(watermark),
                "-filter_complex",
                "[0:v]drawtext="
                "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
                f"text='{safe_text}':fontcolor=white:fontsize=54:line_spacing=12:"
                "box=1:boxcolor=0x111111@0.85:boxborderw=28:x=(w-text_w)/2:y=(h-text_h)/2[txt];"
                f"[2:v]format=rgba,colorchannelmixer=aa={opacity}[wm];"
                "[txt][wm]overlay=W-w-36:H-h-36[v]",
                "-map", "[v]", "-map", "1:a:0", "-t", "4", "-r", "30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                "-movflags", "+faststart", "-metadata", f"brand_id={self.brand_id}",
                "-metadata", f"brand_name={self.config.get('brand_name_en', self.brand_id)}", str(content),
            ],
            check=True,
        )

        segments = []
        for source, target in ((intro, output.with_name(output.stem + ".intro.mp4"),), (outro, output.with_name(output.stem + ".outro.mp4"),)):
            if self._has_audio(source):
                self._normalize_segment_with_audio(source, target)
            else:
                shutil.copy2(source, target)
            segments.append(target)

        concat_file = output.with_name(output.stem + ".concat.txt")
        try:
            concat_file.write_text("\n".join(f"file '{p.resolve()}'" for p in (segments[0], content, segments[1])) + "\n", encoding="utf-8")
            subprocess.run(
                [self.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", "-movflags", "+faststart", str(merged)],
                check=True,
            )
            shutil.move(merged, output)
        finally:
            for path in (*segments, content, merged, concat_file):
                path.unlink(missing_ok=True)
        return str(output)

    def _normalize_segment_with_audio(self, source: Path, target: Path) -> None:
        subprocess.run(
            [self.ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error", "-i", str(source), "-map", "0:v:0", "-map", "0:a:0", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(target)],
            check=True,
        )
