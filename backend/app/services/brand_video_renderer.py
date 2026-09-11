from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BRANDS_DIR = ROOT / "backend" / "app" / "config" / "brands"


class BrandVideoRenderer:
    """Apply configured branding with real FFmpeg processing.

    Intro/outro/watermark media are optional. Missing optional brand media no
    longer turns a valid production render into a fake/synthetic result or an
    unexplained file-not-found crash; the content is still normalized and
    returned as a real MP4.
    """

    def __init__(self, brand_id: str = "afham_wadhak") -> None:
        self.brand_id = brand_id
        self.config_path = BRANDS_DIR / f"{brand_id}.json"
        if not self.config_path.is_file():
            raise FileNotFoundError(f"BRAND_CONFIG_NOT_FOUND:{brand_id}")
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        if self.config.get("brand_id") != brand_id:
            raise ValueError(f"Brand config id mismatch: {self.config.get('brand_id')} != {brand_id}")
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("FFMPEG_NOT_FOUND")

    def _asset(self, name: str) -> Path | None:
        folder = self.config.get("file_structure", {}).get("brand_folder", f"assets/branding/{self.brand_id}/")
        path = ROOT / Path(folder) / name
        return path if path.is_file() else None

    def _has_audio(self, source: Path) -> bool:
        if shutil.which("ffprobe") is None:
            return True
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=index", "-of", "csv=p=0", str(source)],
            capture_output=True,
            text=True,
            check=False,
        )
        return bool(result.stdout.strip())

    def _normalize_source(self, source: Path, target: Path, width: int, height: int, fps: int, watermark: Path | None, opacity: float) -> None:
        video_filter = (
            f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p"
        )
        args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source)]
        if watermark is not None:
            filter_complex = f"[0:v]{video_filter}[v];[1:v]format=rgba,colorchannelmixer=aa={opacity}[wm];[v][wm]overlay=W-w-36:H-h-36[vout]"
            args += ["-loop", "1", "-i", str(watermark), "-filter_complex", filter_complex, "-map", "[vout]"]
        else:
            args += ["-vf", video_filter, "-map", "0:v:0"]
        if self._has_audio(source):
            args += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "192k"]
        else:
            audio_input = 2 if watermark is not None else 1
            args += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-map", f"{audio_input}:a:0", "-c:a", "aac", "-b:a", "192k"]
        args += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target)]
        subprocess.run(args, check=True)

    def _normalize_brand_segment(self, source: Path, target: Path, width: int, height: int, fps: int) -> None:
        video_filter = (
            f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,format=yuv420p"
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
                "-vf", video_filter, "-map", "0:v:0", "-map", "0:a:0?",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(target),
            ],
            check=True,
        )

    def apply(self, source: str | Path, output: str | Path, width: int, height: int, fps: int) -> str:
        source_path = Path(source)
        output_path = Path(output)
        if not source_path.is_file():
            raise FileNotFoundError(f"BRAND_SOURCE_NOT_FOUND:{source_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        intro = self._asset("intro.mp4")
        outro = self._asset("outro.mp4")
        watermark = self._asset("watermark.png") or self._asset("watermark.svg")
        opacity = max(0.0, min(1.0, float(self.config.get("watermark", {}).get("opacity", 0.35))))

        with tempfile.TemporaryDirectory(prefix="acf-brand-") as temp_dir:
            temp = Path(temp_dir)
            branded_content = temp / "content.mp4"
            self._normalize_source(source_path, branded_content, width, height, fps, watermark, opacity)

            if intro is None or outro is None:
                shutil.copy2(branded_content, output_path)
                return str(output_path)

            normalized_intro = temp / "intro.mp4"
            normalized_outro = temp / "outro.mp4"
            concat_file = temp / "concat.txt"
            self._normalize_brand_segment(intro, normalized_intro, width, height, fps)
            self._normalize_brand_segment(outro, normalized_outro, width, height, fps)
            concat_file.write_text(
                "\n".join(f"file '{path.as_posix()}'" for path in (normalized_intro, branded_content, normalized_outro)) + "\n",
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "concat", "-safe", "0", "-i", str(concat_file),
                    "-c", "copy", "-movflags", "+faststart",
                    "-metadata", f"brand_id={self.brand_id}",
                    "-metadata", f"brand_name={self.config.get('brand_name_en', self.brand_id)}",
                    str(output_path),
                ],
                check=True,
            )
        return str(output_path)
