from types import SimpleNamespace
from pathlib import Path

from app.domain.assets import AssetStatus, AssetType
from app.workers.publish_worker import PublishWorker
from app.publishing.adapters import DryRunAdapter, PublishRequest


class _Assets:
    def __init__(self, asset):
        self.asset = asset

    def get(self, asset_id):
        return self.asset if asset_id == self.asset.id else None

    def create(self, asset):
        return asset


class _Storage:
    def __init__(self, path):
        self.path = Path(path)

    def put_bytes(self, payload):
        return "digest", str(self.path), len(payload)


def _job(platforms):
    return SimpleNamespace(
        id="job-1",
        project_id="project-1",
        type=SimpleNamespace(value="PUBLISH"),
        input=SimpleNamespace(
            reference_asset_ids=["asset-1"],
            parameters={"platforms": platforms, "title": "Test", "description": "Description"},
        ),
    )


def test_dry_run_adapter_rejects_missing_asset_path():
    errors = DryRunAdapter().validate(PublishRequest(asset_path="", title="Test"))
    assert errors == ["ASSET_PATH_REQUIRED"]


def test_publish_worker_fails_unknown_platform(tmp_path):
    source = SimpleNamespace(id="asset-1", status=AssetStatus.READY, type=AssetType.VIDEO, path=str(tmp_path / "video.mp4"))
    Path(source.path).write_bytes(b"video")
    worker = PublishWorker(_Storage(tmp_path / "package.json"), _Assets(source))
    worker.initialize()
    result = worker.execute(_job(["unknown"]), SimpleNamespace(report_progress=lambda *_: None))
    assert not result.success
    assert result.error_code == "PUBLISH_PREPARATION_FAILED"
    assert "unknown" in result.error_message


def test_publish_worker_requires_existing_source(tmp_path):
    source = SimpleNamespace(id="asset-1", status=AssetStatus.READY, type=AssetType.VIDEO, path=str(tmp_path / "missing.mp4"))
    worker = PublishWorker(_Storage(tmp_path / "package.json"), _Assets(source))
    worker.initialize()
    result = worker.execute(_job(["youtube"]), SimpleNamespace(report_progress=lambda *_: None))
    assert not result.success
    assert result.error_code == "PUBLISH_ASSET_MISSING"
