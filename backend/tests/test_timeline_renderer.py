from backend.app.domain.timeline import Timeline, TimelineClip, TimelineTrack, TrackType
from backend.app.rendering.ffmpeg_renderer import FfmpegRenderer
from backend.app.rendering.renderer import RenderProfile


def test_timeline_rejects_out_of_bounds_clip():
    timeline = Timeline(id="t1", project_id="p1", duration_us=1_000_000, tracks=[TimelineTrack(id="v1", type=TrackType.VIDEO, clips=[TimelineClip(id="c1", asset_id="a1", start_us=900_000, duration_us=200_000)])])
    assert "CLIP_OUT_OF_BOUNDS:c1" in timeline.validate()


def test_real_renderer_rejects_empty_timeline():
    timeline = Timeline(id="t1", project_id="p1", duration_us=2_000_000)
    errors = FfmpegRenderer({}).validate(timeline, RenderProfile())
    assert "TIMELINE_HAS_NO_VIDEO" in errors
