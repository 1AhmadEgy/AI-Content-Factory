import sys
import time
from pathlib import Path

from app.domain.timeline import Timeline, TimelineClip, TimelineTrack, TrackType
from app.rendering.ffmpeg_renderer import FfmpegRenderOptions, FfmpegRenderer
from app.rendering.renderer import RenderProfile


def _timeline() -> Timeline:
    return Timeline(
        id="render-timeout",
        project_id="project-1",
        duration_us=1_000_000,
        timebase=1_000_000,
        tracks=[
            TimelineTrack(
                id="video",
                type=TrackType.VIDEO,
                clips=[
                    TimelineClip(
                        id="clip-1",
                        asset_id="asset-1",
                        start_us=0,
                        duration_us=1_000_000,
                        source_start_us=0,
                    )
                ],
            )
        ],
    )


def test_ffmpeg_timeout_terminates_process_and_leaves_no_output(tmp_path: Path) -> None:
    sleeper = tmp_path / "fake_ffmpeg.py"
    sleeper.write_text(
        "import time\ntime.sleep(30)\n",
        encoding="utf-8",
    )
    output = tmp_path / "output.mp4"
    renderer = FfmpegRenderer(
        {"asset-1": str(tmp_path / "input.mp4")},
        FfmpegRenderOptions(
            ffmpeg_bin=sys.executable,
            ffprobe_bin=sys.executable,
            timeout_seconds=1,
            cancel_grace_seconds=0.1,
        ),
    )
    renderer._build_args = lambda timeline, profile, destination: [sys.executable, str(sleeper)]
    started = time.monotonic()
    result = renderer.render(_timeline(), RenderProfile("test", 16, 16, 1), str(output))
    elapsed = time.monotonic() - started

    assert not result.success
    assert result.error == "FFMPEG_TIMEOUT"
    assert elapsed < 5
    assert not output.exists()
    assert not renderer._processes
