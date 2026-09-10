from pathlib import Path

from backend.app.domain.assets import AssetType
from backend.app.domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from backend.app.infrastructure.storage import LocalAssetStorage
from backend.app.providers.registry import default_provider_registry
from backend.app.workers.provider_worker import ProviderGenerationWorker


class AssetStore:
    def __init__(self):
        self.items = {}

    def create(self, asset):
        self.items[asset.id] = asset
        return asset

    def get(self, asset_id):
        return self.items.get(asset_id)


def test_provider_generation_worker_routes_and_persists_output(tmp_path: Path) -> None:
    assets = AssetStore()
    worker = ProviderGenerationWorker(default_provider_registry(), LocalAssetStorage(tmp_path), assets)
    worker.initialize()
    job = GenerationJob(
        id="image-1",
        project_id="project-1",
        type=JobType.IMAGE,
        target_type="shot",
        target_id="shot-1",
        status=JobStatus.RUNNING,
        input=JobInput(parameters={"prompt": "cinematic city"}, seed=42, deterministic=True),
    )

    result = worker.execute(job, type("Context", (), {"cancellation_requested": False})())

    assert result.success is True
    assert len(result.asset_ids) == 1
    asset = assets.get(result.asset_ids[0])
    assert asset is not None
    assert asset.type is AssetType.IMAGE
    assert asset.provenance.model == "mock-deterministic"
    assert asset.provenance.job_id == job.id
    assert Path(asset.path).exists()
