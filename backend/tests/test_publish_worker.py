from pathlib import Path
from types import SimpleNamespace

from app.domain.assets import AssetProvenance, AssetStatus, AssetType, LicenseStatus
from app.infrastructure.storage import LocalAssetStorage
from app.publishing.adapters import AdapterRegistry
from app.workers.publish_worker import PublishWorker


class _Assets:
    def __init__(self, asset):
        self.asset = asset

    def get(self, asset_id):
        return self.asset if asset_id == self.asset.id else None

    def create(self, asset):
        self.asset = asset
        return asset


def _job(platforms):
    return SimpleNamespace(
        id="job-1",
        project_id="project-1",
        provider=None,
        model=None,
        parent_job_id=None,
        target_type=None,
        target_id=None,
        type=SimpleNamespace(value="PUBLISH"),
        input=SimpleNamespace(
            reference_asset_ids=["asset-1"],
            parameters={"platforms": platforms, "title": "Test", "description": "Description"},
            seed=None,
        ),
    )


def test_default_registry_has_no_unconfigured_publishing_provider(monkeypatch):
    for platform in ("YOUTUBE", "TIKTOK", "INSTAGRAM", "FACEBOOK"):
        monkeypatch.delenv(f"AICF_PUBLISH_{platform}_ENDPOINT", raising=False)
    assert AdapterRegistry().names() == []


def test_publish_worker_fails_unknown_platform(tmp_path):
    storage = LocalAssetStorage(tmp_path)
    source_path = tmp_path / "video.mp4"
    source_path.write_bytes(b"video")
    digest, stored_path, size = storage.put_file(source_path)
    source = SimpleNamespace(id="asset-1", project_id="project-1", status=AssetStatus.READY, type=AssetType.VIDEO, path=stored_path, sha256=digest, size_bytes=size, provenance=AssetProvenance(job_id="source-job", license_status=LicenseStatus.VERIFIED))
    worker = PublishWorker(storage, _Assets(source), AdapterRegistry())
    worker.initialize()
    result = worker.execute(_job(["unknown"]), SimpleNamespace(report_progress=lambda *_: None))
    assert not result.success
    assert result.error_code == "PUBLISH_PREPARATION_FAILED"
    assert "unknown" in result.error_message


def test_publish_worker_requires_existing_source(tmp_path):
    storage = LocalAssetStorage(tmp_path)
    source = SimpleNamespace(id="asset-1", project_id="project-1", status=AssetStatus.READY, type=AssetType.VIDEO, path=str(tmp_path / "missing.mp4"), sha256="0" * 64, size_bytes=5, provenance=AssetProvenance(job_id="source-job", license_status=LicenseStatus.VERIFIED))
    worker = PublishWorker(storage, _Assets(source), AdapterRegistry())
    worker.initialize()
    result = worker.execute(_job(["youtube"]), SimpleNamespace(report_progress=lambda *_: None))
    assert not result.success
    assert result.error_code == "PUBLISH_ASSET_INTEGRITY_FAILED"
