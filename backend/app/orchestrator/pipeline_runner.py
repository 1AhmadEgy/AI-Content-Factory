from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..application.pipeline import AssetCheckInput, MediaPipelineService
from ..domain.best_take import TakeCandidate
from ..domain.timeline import Timeline
from ..rendering.renderer import DeterministicMockRenderer, RenderProfile


@dataclass(frozen=True, slots=True)
class PipelineRunResult:
    qc_passed: bool
    best_asset_id: str | None
    rendered_path: str | None
    errors: list[str]


class PipelineRunner:
    """Deterministic end-to-end media runner used by mock/offline mode."""

    def __init__(self, service: MediaPipelineService | None = None) -> None:
        self.service = service or MediaPipelineService()

    def run(
        self,
        *,
        assets: list[AssetCheckInput],
        candidates: list[TakeCandidate],
        timeline: Timeline,
        output_path: str,
    ) -> PipelineRunResult:
        qc_results = {item.asset_id: self.service.qc_asset(item) for item in assets}
        best = self.service.select_take(candidates, qc_results)
        if best is None:
            errors = [
                finding.code
                for result in qc_results.values()
                for finding in result.findings
                if not result.passed
            ]
            return PipelineRunResult(False, None, None, errors + ["NO_ELIGIBLE_BEST_TAKE"])

        # Candidate-level failures are expected during best-take selection. A
        # pipeline run is QC-passing when the selected take itself passed QC;
        # rejected alternative takes must not invalidate the final result.
        selected_qc = qc_results[best.asset_id]
        selected_errors = [finding.code for finding in selected_qc.findings if not selected_qc.passed]
        if selected_errors or selected_qc.blocked:
            return PipelineRunResult(False, best.asset_id, None, selected_errors or ["SELECTED_TAKE_BLOCKED"])

        renderer = DeterministicMockRenderer()
        result = self.service.render(renderer, timeline, RenderProfile(), str(Path(output_path)))
        if not result.success:
            return PipelineRunResult(False, best.asset_id, None, [result.error or "RENDER_FAILED"])
        return PipelineRunResult(True, best.asset_id, result.output_path, [])
