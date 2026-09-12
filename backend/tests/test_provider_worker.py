from pathlib import Path

from app.domain.assets import AssetType
from app.domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from app.infrastructure.storage import LocalAssetStorage
from app.providers.contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse
from app.providers.registry import ModelRegistry, RegisteredModel
from app.workers.provider_worker import ProviderGenerationWorker


class AssetStore:
    def __init__(self): self.items = {}
    def create(self, asset): self.items[asset.id] = asset; return asset
    def get(self, asset_id): return self.items.get(asset_id)


class BinaryImageAdapter(ModelAdapter):
    def capability(self):
        return ModelCapability(category="generation", capabilities=frozenset({"generation", "image", "real-provider"}), runtime="TEST")

    def health_check(self):
        return True

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(success=True, output_bytes=b"PNG-DATA", output_mime_type="image/png", output_metadata={"width": 64, "height": 64}, provider_run_id="binary-1", metrics={"score": 0.9})

    def cancel(self, provider_run_id: str) -> bool:
        return False


def test_provider_generation_worker_routes_and_persists_binary_output(tmp_path: Path) -> None:
    assets = AssetStore()
    registry = ModelRegistry()
    registry.register(RegisteredModel(id="binary-image", provider="test", adapter=BinaryImageAdapter(), enabled=True, priority=1))
    worker = ProviderGenerationWorker(registry, LocalAssetStorage(tmp_path), assets)
    worker.initialize()
    job = GenerationJob(id="image-1", project_id="project-1", type=JobType.IMAGE, target_type="shot", target_id="shot-1", model="binary-image", status=JobStatus.RUNNING, input=JobInput(parameters={"prompt": "cinematic city"}, seed=42, deterministic=True))
    result = worker.execute(job, type("Context", (), {"cancellation_requested": False})())
    assert result.success is True
    assert len(result.asset_ids) == 1
    asset = assets.get(result.asset_ids[0])
    assert asset is not None
    assert asset.type is AssetType.IMAGE
    assert asset.provenance.model == "binary-image"
    assert asset.provenance.job_id == job.id
    assert Path(asset.path).exists()


def test_provider_generation_worker_rejects_missing_real_media_provider(tmp_path: Path) -> None:
    assets = AssetStore()
    registry = ModelRegistry()
    worker = ProviderGenerationWorker(registry, LocalAssetStorage(tmp_path), assets)
    worker.initialize()
    job = GenerationJob(id="video-1", project_id="project-1", type=JobType.VIDEO, target_type="shot", target_id="shot-1", status=JobStatus.RUNNING, input=JobInput(parameters={"prompt": "motion"}))
    result = worker.execute(job, type("Context", (), {"cancellation_requested": False})())
    assert result.success is False
    assert result.error_code == "MODEL_CAPABILITY_UNAVAILABLE"
