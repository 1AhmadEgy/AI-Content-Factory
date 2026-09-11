from backend.app.domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from backend.app.infrastructure.storage import LocalAssetStorage
from backend.app.orchestrator.queue import WorkerContext
from backend.app.workers.timeline_worker import TimelineWorker


class Assets:
    def __init__(self):
        self.items = set()

    def get(self, asset_id):
        return object() if asset_id in self.items else None

    def create(self, asset):
        self.items.add(asset.id)
        return asset


def test_timeline_worker_rejects_non_asset_repository_records(tmp_path):
    storage = LocalAssetStorage(tmp_path)
    assets = Assets()
    assets.items.update({"asset-1", "asset-2"})
    worker = TimelineWorker(storage, assets)
    worker.initialize()
    job = GenerationJob(id="timeline-job", project_id="project-1", type=JobType.TIMELINE, target_type="timeline", status=JobStatus.QUEUED, input=JobInput(reference_asset_ids=["asset-1", "asset-2"], parameters={"durationUs": 2_000_000}))
    result = worker.execute(job, WorkerContext(worker_id="timeline", lease_id="lease"))
    assert result.success is False
    assert result.error_code == "TIMELINE_NO_VIDEO"
