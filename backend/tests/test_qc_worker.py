from pathlib import Path

from backend.app.domain.assets import Asset, AssetProvenance, AssetStatus, AssetType, LicenseStatus
from backend.app.domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from backend.app.infrastructure.storage import LocalAssetStorage
from backend.app.workers.qc_worker import QualityControlWorker


class AssetStore:
    def __init__(self):
        self.items = {}

    def create(self, asset):
        self.items[asset.id] = asset
        return asset

    def get(self, asset_id):
        return self.items.get(asset_id)


def _job(project_id: str = "project-1") -> GenerationJob:
    return GenerationJob(
        id="qc-1",
        project_id=project_id,
        type=JobType.QC,
        target_type="asset",
        target_id="asset-1",
        status=JobStatus.RUNNING,
        input=JobInput(reference_asset_ids=["asset-1"]),
    )


def _asset(storage: LocalAssetStorage, project_id: str = "project-1") -> Asset:
    payload = b"real-media-bytes"
    digest, path, size = storage.put_bytes(payload)
    return Asset(
        id="asset-1",
        project_id=project_id,
        type=AssetType.VIDEO,
        path=path,
        mime_type="video/mp4",
        size_bytes=size,
        sha256=digest,
        status=AssetStatus.READY,
        provenance=AssetProvenance(license_status=LicenseStatus.VERIFIED),
    )


def _context():
    return type("Context", (), {"cancellation_requested": False})()


def test_qc_rejects_asset_from_another_project(tmp_path: Path) -> None:
    storage = LocalAssetStorage(tmp_path)
    assets = AssetStore()
    assets.create(_asset(storage, project_id="project-2"))
    worker = QualityControlWorker(storage, assets)
    worker.initialize()

    result = worker.execute(_job(project_id="project-1"), _context())

    assert result.success is False
    assert result.error_code == "QC_FAILED"
    report = assets.items[result.asset_ids[0]]
    report_payload = Path(report.path).read_text(encoding="utf-8")
    assert '"projectMatch": false' in report_payload
    assert '"passed": false' in report_payload


def test_qc_passes_only_for_owned_verified_intact_ready_asset(tmp_path: Path) -> None:
    storage = LocalAssetStorage(tmp_path)
    assets = AssetStore()
    assets.create(_asset(storage))
    worker = QualityControlWorker(storage, assets)
    worker.initialize()

    result = worker.execute(_job(), _context())

    assert result.success is True
    assert result.error_code is None
    report = assets.items[result.asset_ids[0]]
    report_payload = Path(report.path).read_text(encoding="utf-8")
    assert '"projectMatch": true' in report_payload
    assert '"checksum": true' in report_payload
    assert '"licenseVerified": true' in report_payload
    assert '"passed": true' in report_payload
