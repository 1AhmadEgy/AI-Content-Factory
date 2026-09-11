from pathlib import Path
from types import SimpleNamespace

from app.domain.assets import AssetProvenance, AssetStatus, AssetType, LicenseStatus
from app.publishing.adapters import AdapterRegistry, PublishRequest, PublishingAdapter, PublishResult
from app.workers.publish_worker import PublishWorker


class _Assets:
    def __init__(self, asset):
        self.asset = asset
        self.created = []

    def get(self, asset_id):
        return self.asset if asset_id == self.asset.id else None

    def create(self, asset):
        self.created.append(asset)
        return asset


class _Storage:
    def __init__(self, path):
        self.path = Path(path)

    def put_bytes(self, payload):
        self.path.write_bytes(payload)
        return "digest", str(self.path), len(payload)

    def verify(self, asset):
        return Path(asset.path).is_file() and Path(asset.path).stat().st_size == asset.size_bytes


class _PublishingAdapter(PublishingAdapter):
    name = "test"

    def validate(self, request: PublishRequest) -> list[str]:
        return [] if request.asset_path else ["ASSET_PATH_REQUIRED"]

    def publish(self, request: PublishRequest) -> PublishResult:
        return PublishResult(self.name, "PUBLISHED", external_id="external-1", payload={"ok": True})


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


def _source(tmp_path):
    path = tmp_path / "video.mp4"
    path.write_bytes(b"real-video")
    return SimpleNamespace(
        id="asset-1",
        project_id="project-1",
        status=AssetStatus.READY,
        type=AssetType.VIDEO,
        path=str(path),
        size_bytes=path.stat().st_size,
        provenance=AssetProvenance(license_status=LicenseStatus.VERIFIED),
    )


def test_publish_request_rejects_missing_asset_path():
    errors = _PublishingAdapter().validate(PublishRequest(asset_path="", title="Test"))
    assert errors == ["ASSET_PATH_REQUIRED"]


def test_publish_worker_fails_unknown_platform(tmp_path):
    source = _source(tmp_path)
    worker = PublishWorker(_Storage(tmp_path / "package.json"), _Assets(source))
    worker.initialize()
    result = worker.execute(_job(["unknown"]), SimpleNamespace(report_progress=lambda *_: None))
    assert not result.success
    assert result.error_code == "PUBLISH_FAILED"
    assert "unknown" in result.error_message


def test_publish_worker_requires_existing_source(tmp_path):
    source = _source(tmp_path)
    Path(source.path).unlink()
    worker = PublishWorker(_Storage(tmp_path / "package.json"), _Assets(source))
    worker.initialize()
    result = worker.execute(_job(["youtube"]), SimpleNamespace(report_progress=lambda *_: None))
    assert not result.success
    assert result.error_code == "PUBLISH_ASSET_MISSING"


def test_publish_worker_accepts_real_external_id(tmp_path):
    source = _source(tmp_path)
    adapters = AdapterRegistry([_PublishingAdapter()])
    assets = _Assets(source)
    worker = PublishWorker(_Storage(tmp_path / "package.json"), assets, adapters)
    worker.initialize()
    result = worker.execute(_job(["test"]), SimpleNamespace(report_progress=lambda *_: None))
    assert result.success
    assert result.metrics["status"] == "PUBLISHED"
    assert assets.created[-1].type is AssetType.DOCUMENT
