from pathlib import Path

from app.domain.assets import AssetType
from app.domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from app.infrastructure.storage import LocalAssetStorage
from app.providers.contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse
from app.providers.registry import ModelRegistry, RegisteredModel
from app.workers.provider_worker import ProviderGenerationWorker


class AssetStore:
    def __init__(self):
        self.items = {}
        self.create_calls = 0

    def create(self, asset):
        self.create_calls += 1
        self.items[asset.id] = asset
        return asset

    def get(self, asset_id):
        return self.items.get(asset_id)


class CountingImageAdapter(ModelAdapter):
    calls = 0

    def capability(self):
        return ModelCapability(category="generation", capabilities=frozenset({"generation", "image", "real-provider"}), runtime="TEST")

    def health_check(self):
        return True

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        type(self).calls += 1
        return ProviderResponse(success=True, output_bytes=b"same-image", output_mime_type="image/png", provider_run_id=f"run-{self.calls}")

    def cancel(self, provider_run_id: str) -> bool:
        return False


def test_provider_output_asset_is_idempotent_across_retries(tmp_path: Path) -> None:
    assets = AssetStore()
    registry = ModelRegistry()
    CountingImageAdapter.calls = 0
    registry.register(RegisteredModel(id="counting-image", provider="test", adapter=CountingImageAdapter(), enabled=True, priority=1))
    worker = ProviderGenerationWorker(registry, LocalAssetStorage(tmp_path), assets)
    worker.initialize()
    job = GenerationJob(id="retry-job", project_id="project-1", type=JobType.IMAGE, target_type="shot", target_id="shot-1", model="counting-image", status=JobStatus.RUNNING, input=JobInput(parameters={"prompt": "same"}, seed=7, deterministic=True))

    first = worker.execute(job, type("Context", (), {"cancellation_requested": False})())
    second = worker.execute(job, type("Context", (), {"cancellation_requested": False})())

    assert first.success is True
    assert second.success is True
    assert first.asset_ids == second.asset_ids
    assert len(assets.items) == 1
    assert assets.create_calls == 1
    assert assets.get(first.asset_ids[0]).type is AssetType.IMAGE
    assert Path(assets.get(first.asset_ids[0]).path).exists()
