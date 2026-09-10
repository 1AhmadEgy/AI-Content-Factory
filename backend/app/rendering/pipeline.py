from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .media_artifacts import create_provenance_manifest, extract_thumbnail, write_metadata_sidecar
from .media_qc import FinalMediaQC, QcThresholds
from .renderer import RenderProfile, Renderer


@dataclass(frozen=True, slots=True)
class FinalizeResult:
    output_path: str
    thumbnail_path: str
    metadata_path: str
    provenance_path: str
    qc: dict


class MediaFinalizePipeline:
    """Render -> probe/decode QC -> thumbnail -> metadata -> provenance. Promotion is the final step."""

    def __init__(self, renderer: Renderer, qc: FinalMediaQC | None = None):
        self.renderer = renderer
        self.qc = qc or FinalMediaQC()

    def execute(self, timeline, profile: RenderProfile, staging_output: str, final_output: str, *, metadata: Mapping[str, str], source_assets: Mapping[str, str], timeline_version: str = "1", renderer_version: str = "unknown") -> FinalizeResult:
        result = self.renderer.render(timeline, profile, staging_output)
        if not result.success or not result.output_path:
            raise RuntimeError(result.error or "RENDER_FAILED")
        qc = self.qc.run(result.output_path, expected_duration_s=timeline.duration_us / 1_000_000, thresholds=QcThresholds())
        if not qc["passed"]:
            Path(result.output_path).unlink(missing_ok=True)
            raise RuntimeError("FINAL_QC_FAILED:" + ";".join(qc["errors"]))
        final = Path(final_output)
        final.parent.mkdir(parents=True, exist_ok=True)
        Path(result.output_path).replace(final)
        thumbnail = str(final.with_suffix(".jpg"))
        extract_thumbnail(str(final), thumbnail, min(1.0, timeline.duration_us / 1_000_000))
        metadata_path = write_metadata_sidecar(str(final.with_suffix(final.suffix + ".metadata.json")), metadata)
        provenance = create_provenance_manifest(str(final), timeline_id=timeline.id, timeline_version=timeline_version, render_profile=profile.name, renderer=type(self.renderer).__name__, renderer_version=renderer_version, source_assets=source_assets, qc=qc)
        return FinalizeResult(str(final), thumbnail, metadata_path, provenance, qc)
