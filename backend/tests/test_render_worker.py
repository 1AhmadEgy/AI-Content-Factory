from app.workers.render_worker import RenderWorker


def test_render_resolution_presets_are_codec_safe():
    assert RenderWorker._resolution({"resolution": "720p", "aspectRatio": "16:9"}) == (1280, 720)
    assert RenderWorker._resolution({"resolution": "1080p", "aspectRatio": "9:16"}) == (608, 1080)
    assert RenderWorker._resolution({"resolution": "4k", "aspectRatio": "1:1"}) == (2160, 2160)


def test_render_requires_timeline_without_progress_context():
    worker = RenderWorker.__new__(RenderWorker)
    worker._initialized = True
    result = worker.execute(type("Job", (), {"input": type("Input", (), {"reference_asset_ids": []})()})(), None)
    assert not result.success
    assert result.error_code == "RENDER_NO_TIMELINE"
