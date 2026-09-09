from __future__ import annotations

from dataclasses import dataclass

from ..domain.best_take import TakeCandidate, select_best_take
from ..domain.qc import QcResult, evaluate_asset
from ..domain.timeline import Timeline
from ..rendering.renderer import RenderProfile, RenderResult, Renderer


@dataclass(frozen=True, slots=True)
class AssetCheckInput:
    asset_id: str
    readable: bool
    size_bytes: int
    license_status: str
    required_mime: str | None = None
    actual_mime: str | None = None


class MediaPipelineService:
    """Coordinates deterministic media stages without depending on providers."""

    def qc_asset(self, item: AssetCheckInput) -> QcResult:
        return evaluate_asset(
            asset_id=item.asset_id,
            readable=item.readable,
            size_bytes=item.size_bytes,
            license_status=item.license_status,
            required_mime=item.required_mime,
            actual_mime=item.actual_mime,
        )

    def select_take(self, candidates: list[TakeCandidate], qc_results: dict[str, QcResult]) -> TakeCandidate | None:
        return select_best_take(candidates, qc_results)

    def render(self, renderer: Renderer, timeline: Timeline, profile: RenderProfile, output_path: str) -> RenderResult:
        return renderer.render(timeline, profile, output_path)
