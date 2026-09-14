from pathlib import Path

from app.application.pipeline import AssetCheckInput
from app.domain.best_take import TakeCandidate
from app.domain.timeline import Timeline
from app.orchestrator.pipeline_runner import PipelineRunner


def test_pipeline_runner_fails_closed_when_timeline_has_no_video(tmp_path: Path):
    output = tmp_path / "final.mp4"
    result = PipelineRunner().run(
        assets=[
            AssetCheckInput(
                asset_id="asset-good",
                readable=True,
                size_bytes=100,
                license_status="VERIFIED",
            ),
            AssetCheckInput(
                asset_id="asset-blocked",
                readable=True,
                size_bytes=100,
                license_status="BLOCKED",
            ),
        ],
        candidates=[
            TakeCandidate("asset-good", 1.0, 0.9, 0.95, 1.0),
            TakeCandidate("asset-blocked", 1.0, 1.0, 1.0, 1.0),
        ],
        timeline=Timeline(id="timeline-1", project_id="project-1", duration_us=2_000_000),
        output_path=str(output),
    )
    assert result.best_asset_id == "asset-good"
    assert result.rendered_path is None
    assert result.qc_passed is False
    assert "TIMELINE_HAS_NO_VIDEO" in result.errors
    assert not output.exists()
