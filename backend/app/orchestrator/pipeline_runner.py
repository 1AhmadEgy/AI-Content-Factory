from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from ..application.pipeline import AssetCheckInput, MediaPipelineService
from ..domain.best_take import TakeCandidate
from ..domain.timeline import Timeline
from ..rendering.ffmpeg_renderer import FfmpegRenderer, FfmpegRenderOptions
from ..rendering.media_artifacts import SubtitleCue, create_provenance_manifest, extract_thumbnail, sha256_file, write_metadata_sidecar, write_srt
from ..rendering.renderer import RenderProfile


@dataclass(frozen=True, slots=True)
class PipelineRunResult:
    qc_passed: bool
    best_asset_id: str | None
    rendered_path: str | None
    errors: list[str]
    thumbnail_path: str | None = None
    metadata_path: str | None = None
    provenance_path: str | None = None
    sha256: str | None = None


class PipelineRunner:
    """End-to-end media runner. Rendering is always real FFmpeg; there is no fake output mode."""

    def __init__(self, service: MediaPipelineService | None = None, *, assets: dict[str, str] | None = None, production: bool = True, ffmpeg_options: FfmpegRenderOptions | None = None) -> None:
        if not production:
            raise ValueError("SIMULATED_RENDER_MODE_REMOVED")
        self.service = service or MediaPipelineService()
        self.assets = assets or {}
        self.ffmpeg_options = ffmpeg_options or FfmpegRenderOptions()

    def _renderer(self) -> FfmpegRenderer:
        renderer = FfmpegRenderer(self.assets, self.ffmpeg_options)
        health = renderer.health_check()
        if not health["available"]:
            raise RuntimeError("FFMPEG_UNAVAILABLE")
        return renderer

    def run(self, *, assets: list[AssetCheckInput], candidates: list[TakeCandidate], timeline: Timeline, output_path: str, subtitle_cues: list[SubtitleCue] | None = None, metadata: dict[str, str] | None = None) -> PipelineRunResult:
        qc_results = {item.asset_id: self.service.qc_asset(item) for item in assets}
        best = self.service.select_take(candidates, qc_results)
        if best is None:
            errors = [finding.code for result in qc_results.values() for finding in result.findings if not result.passed]
            return PipelineRunResult(False, None, None, errors + ["NO_ELIGIBLE_BEST_TAKE"])
        selected_qc = qc_results[best.asset_id]
        selected_errors = [finding.code for finding in selected_qc.findings if not selected_qc.passed]
        if selected_errors or selected_qc.blocked:
            return PipelineRunResult(False, best.asset_id, None, selected_errors or ["SELECTED_TAKE_BLOCKED"])

        renderer: FfmpegRenderer | None = None
        staging_path: Path | None = None
        final_path = Path(output_path)
        profile = RenderProfile()
        if final_path.exists() and not self.ffmpeg_options.overwrite:
            return PipelineRunResult(False, best.asset_id, None, ["OUTPUT_EXISTS"])
        try:
            renderer = self._renderer()
            final_path.parent.mkdir(parents=True, exist_ok=True)
            staging_path = final_path.with_name(f".{final_path.stem}.staging-{uuid4().hex}.mp4")
            result = self.service.render(renderer, timeline, profile, str(staging_path))
            if not result.success or not result.output_path:
                return PipelineRunResult(False, best.asset_id, None, [result.error or "RENDER_FAILED"])
            probe = renderer.probe(str(staging_path))
            streams = probe.get("streams", [])
            if not streams or not any(s.get("codec_type") == "video" for s in streams):
                return PipelineRunResult(False, best.asset_id, None, ["QC_NO_VIDEO_STREAM"])
            if not any(s.get("codec_type") == "audio" for s in streams):
                return PipelineRunResult(False, best.asset_id, None, ["QC_NO_AUDIO_STREAM"])
            staging_path.replace(final_path)
            staging_path = None
            thumb = extract_thumbnail(str(final_path), str(final_path.with_suffix(".jpg")))
            meta = write_metadata_sidecar(str(final_path.with_suffix(".metadata.json")), metadata or {})
            digest = sha256_file(str(final_path))
            provenance = create_provenance_manifest(str(final_path), timeline_id=timeline.id, timeline_version="1", render_profile=profile.name, renderer=type(renderer).__name__, renderer_version="1", source_assets=self.assets, qc={"passed": True, "sha256": digest})
            if subtitle_cues:
                write_srt(subtitle_cues, str(final_path.with_suffix(".srt")))
            return PipelineRunResult(True, best.asset_id, str(final_path), [], thumb, meta, provenance, digest)
        except Exception as exc:
            return PipelineRunResult(False, best.asset_id, None, [str(exc)])
        finally:
            if staging_path is not None:
                staging_path.unlink(missing_ok=True)
            if renderer is not None:
                renderer.shutdown()
