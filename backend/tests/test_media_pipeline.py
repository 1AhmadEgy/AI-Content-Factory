from pathlib import Path

from app.domain.timeline import Timeline
from app.rendering.ffmpeg_renderer import FfmpegRenderer
from app.rendering.media_artifacts import SubtitleCue, write_srt
from app.rendering.media_qc import FinalMediaQC
from app.rendering.renderer import RenderProfile
from app.rendering.repurpose import variants_for
from app.security.media_security import safe_child


def test_subtitles_are_valid_srt(tmp_path: Path):
    target = tmp_path / "captions.srt"
    write_srt([SubtitleCue(0, 1200, "مرحبا")], str(target))
    assert "00:00:00,000 --> 00:00:01,200" in target.read_text(encoding="utf-8")


def test_repurpose_variants_are_deterministic():
    names = [v.name for v in variants_for(30)]
    assert names == ["vertical_short", "square", "horizontal"]


def test_path_traversal_is_blocked(tmp_path: Path):
    try:
        safe_child(str(tmp_path), "../secret.mp4")
    except ValueError as exc:
        assert str(exc) == "PATH_TRAVERSAL_BLOCKED"
    else:
        raise AssertionError("traversal was not blocked")


def test_real_renderer_validates_required_video_track():
    timeline = Timeline("t1", "p1", 1_000_000)
    errors = FfmpegRenderer({}).validate(timeline, RenderProfile())
    assert "TIMELINE_HAS_NO_VIDEO" in errors
