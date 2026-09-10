from pathlib import Path

from backend.app.application.pipeline import AssetCheckInput
from backend.app.domain.best_take import TakeCandidate
from backend.app.domain.timeline import Timeline, TimelineClip, TimelineTrack, TrackType
from backend.app.orchestrator.pipeline_runner import PipelineRunner


def test_golden_mock_pipeline_qc_best_take_render(tmp_path: Path):
    output = tmp_path / "final.mp4"
    timeline = Timeline(
        id="timeline-1",
        project_id="project-1",
        duration_us=2_000_000,
        tracks=[
            TimelineTrack(
                id="video-1",
                type=TrackType.VIDEO,
                clips=[TimelineClip("clip-1", "asset-good", 0, 2_000_000)],
            )
        ],
    )
    result = PipelineRunner(production=False).run(
        assets=[
            AssetCheckInput(asset_id="asset-good", readable=True, size_bytes=100, license_status="VERIFIED"),
            AssetCheckInput(asset_id="asset-blocked", readable=True, size_bytes=100, license_status="BLOCKED"),
        ],
        candidates=[
            TakeCandidate("asset-good", 1.0, 0.9, 0.95, 1.0),
            TakeCandidate("asset-blocked", 1.0, 1.0, 1.0, 1.0),
        ],
        timeline=timeline,
        output_path=str(output),
    )
    assert result.best_asset_id == "asset-good"
    assert result.rendered_path == str(output)
    assert output.exists()
    assert result.qc_passed is True
    assert result.sha256
    assert result.provenance_path
