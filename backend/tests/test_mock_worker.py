from pathlib import Path

from backend.app.domain.assets import AssetStatus, AssetType
from backend.app.domain.jobs import GenerationJob, JobInput, JobType
from backend.app.infrastructure.asset_repository import SQLiteAssetRepository
from backend.app.infrastructure.sqlite import SQLiteRepositories
from backend.app.infrastructure.storage import LocalAssetStorage
from backend.app.orchestrator.queue import WorkerContext
from backend.app.workers.mock_worker import DeterministicMockWorker


def test_mock_worker_creates_verifiable_asset(tmp_path: Path) -> None:
    repositories = SQLiteRepositories(":memory:")
    try:
        from backend.app.domain.projects import Project

        repositories.projects.create(Project(id="project-1", name="Demo"))
        assets = SQLiteAssetRepository(repositories.store)
        worker = DeterministicMockWorker(LocalAssetStorage(tmp_path / "assets"), assets)
        worker.initialize()

        job = GenerationJob(
            id="job-1",
            project_id="project-1",
            type=JobType.IMAGE,
            target_type="shot",
            input=JobInput(parameters={"prompt": "a blue room"}, seed=7, deterministic=True),
        )
        result = worker.execute(job, WorkerContext(worker_id="mock-1", lease_id="lease-1"))

        assert result.success is True
        assert len(result.asset_ids) == 1
        asset = assets.get(result.asset_ids[0])
        assert asset is not None
        assert asset.type is AssetType.IMAGE
        assert asset.status is AssetStatus.READY
        assert asset.provenance.provider == "mock"
        assert asset.provenance.license_status.value == "VERIFIED"
        assert Path(asset.path).is_file()
        assert worker.storage.verify(asset)
    finally:
        repositories.close()
