from types import SimpleNamespace

from app.domain.assets import AssetStatus, AssetType, LicenseStatus
from app.domain.jobs import GenerationJob, JobInput, JobOutput, JobStatus, JobType
from app.infrastructure.storage import LocalAssetStorage
from app.workers.timeline_worker import TimelineWorker
from app.orchestrator.queue import WorkerContext


class Assets:
    def __init__(self):
        self.items = {}
        self.created = []

    def get(self, asset_id):
        return self.items.get(asset_id)

    def create(self, asset):
        self.items[asset.id] = asset
        self.created.append(asset)
        return asset


def test_timeline_worker_builds_valid_manifest(tmp_path):
    storage = LocalAssetStorage(tmp_path)
    assets = Assets()
    provenance = SimpleNamespace(license_status=LicenseStatus.VERIFIED)
    for asset_id in ("asset-1", "asset-2"):
        assets.items[asset_id] = SimpleNamespace(
            id=asset_id,
            project_id="project-1",
            type=AssetType.IMAGE,
            status=AssetStatus.READY,
            provenance=provenance,
        )
    worker = TimelineWorker(storage, assets)
    worker.initialize()
    job = GenerationJob(
        id="timeline-job", project_id="project-1", type=JobType.TIMELINE,
        target_type="timeline", status=JobStatus.QUEUED,
        input=JobInput(reference_asset_ids=["asset-1", "asset-2"], parameters={"durationUs": 2_000_000}),
        output=JobOutput(),
    )
    result = worker.execute(job, WorkerContext(worker_id="timeline", lease_id="lease"))
    assert result.success is True
    assert len(result.asset_ids) == 1
    assert len(assets.created) == 1
    assert assets.created[0].type.value == "DOCUMENT"
