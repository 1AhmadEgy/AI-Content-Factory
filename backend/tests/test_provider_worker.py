from pathlib import Path

from backend.app.domain.assets import AssetType
from backend.app.domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from backend.app.infrastructure.storage import LocalAssetStorage
from backend.app.providers.builtin import MockModelAdapter
from backend.app.providers.contracts import ModelCapability, ProviderRequest, ProviderResponse
from backend.app.providers.registry import ModelRegistry, RegisteredModel, default_provider_registry
from backend.app.workers.provider_worker import ProviderGenerationWorker


class AssetStore:
    def __init__(self): self.items = {}
    def create(self, asset): self.items[asset.id] = asset; return asset
    def get(self, asset_id): return self.items.get(asset_id)


def test_provider_generation_worker_routes_and_persists_output(tmp_path: Path) -> None:
    assets = AssetStore()
    worker = ProviderGenerationWorker(default_provider_registry(), LocalAssetStorage(tmp_path), assets)
    worker.initialize()
    job = GenerationJob(id="image-1", project_id="project-1", type=JobType.IMAGE, target_type="shot", target_id="shot-1", status=JobStatus.RUNNING, input=JobInput(parameters={"prompt": "cinematic city"}, seed=42, deterministic=True))
    result = worker.execute(job, type("Context", (), {"cancellation_requested": False})())
    assert result.success is True
    assert len(result.asset_ids) == 1
    asset = assets.get(result.asset_ids[0])
    assert asset is not None
    assert asset.type is AssetType.IMAGE
    assert asset.provenance.model == "mock-deterministic"
    assert asset.provenance.job_id == job.id
    assert Path(asset.path).exists()


class BinaryAdapter(MockModelAdapter):
    def execute(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(success=True, output_bytes=b"PNG-DATA", output_mime_type="image/png", output_metadata={"width": 64, "height": 64}, provider_run_id="binary-1", metrics={"score": 0.9})


def test_provider_generation_worker_persists_binary_media(tmp_path: Path) -> None:
    assets = AssetStore()
    registry = ModelRegistry()
    registry.register(RegisteredModel(id="binary-image", provider="test", adapter=BinaryAdapter("binary-image"), enabled=True, priority=1))
    worker = ProviderGenerationWorker(registry, LocalAssetStorage(tmp_path), assets)
    worker.initialize()
    job = GenerationJob(id="image-binary", project_id="project-1", type=JobType.IMAGE, target_type="shot", target_id="shot-1", model="binary-image", status=JobStatus.RUNNING, input=JobInput(parameters={"prompt": "city"}))
    result = worker.execute(job, type("Context", (), {"cancellation_requested": False})())
    assert result.success is True
    asset = assets.get(result.asset_ids[0])
    assert asset.mime_type == "image/png"
    assert Path(asset.path).read_bytes() == b"PNG-DATA"
