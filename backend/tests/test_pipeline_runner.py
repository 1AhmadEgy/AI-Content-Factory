from backend.app.application.pipeline import AssetCheckInput
from backend.app.domain.best_take import TakeCandidate
from backend.app.domain.timeline import Timeline
from backend.app.orchestrator.pipeline_runner import PipelineRunner


def test_pipeline_runner_requires_real_video_timeline():
    result = PipelineRunner().run(
        assets=[AssetCheckInput(asset_id="asset-good", readable=True, size_bytes=100, license_status="VERIFIED"), AssetCheckInput(asset_id="asset-blocked", readable=True, size_bytes=100, license_status="BLOCKED")],
        candidates=[TakeCandidate("asset-good", 1.0, 0.9, 0.95, 1.0), TakeCandidate("asset-blocked", 1.0, 1.0, 1.0, 1.0)],
        timeline=Timeline(id="timeline-1", project_id="project-1", duration_us=2_000_000),
        output_path="/tmp/should-not-render.mp4",
    )
    assert result.best_asset_id == "asset-good"
    assert result.qc_passed is False
    assert result.rendered_path is None
    assert "TIMELINE_HAS_NO_VIDEO" in result.errors
