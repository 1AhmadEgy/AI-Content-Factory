from pathlib import Path

from backend.app.domain.assets import AssetType
from backend.app.domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from backend.app.infrastructure.storage import LocalAssetStorage
from backend.app.providers.registry import ModelRegistry, default_provider_registry
from backend.app.workers.provider_worker import ProviderGenerationWorker


class AssetStore:
    def __init__(self): self.items = {}
    def create(self, asset): self.items[asset.id] = asset; return asset
    def get(self, asset_id): return self.items.get(asset_id)


def _job(job_id: str = "image-1") -> GenerationJob:
    return GenerationJob(
        id=job_id,
        project_id="project-1",
        type=JobType.IMAGE,
        target_type="shot",
        target_id="shot-1",
        status=JobStatus.RUNNING,
        input=JobInput(parameters={"prompt": "cinematic city"}, seed=42),
    )


def test_provider_generation_worker_does_not_succeed_without_real_provider(tmp_path: Path) -> None:
    assets = AssetStore()
    worker = ProviderGenerationWorker(ModelRegistry(), LocalAssetStorage(tmp_path), assets)
    worker.initialize()
    result = worker.execute(_job(), type("Context", (), {"cancellation_requested": False})())
    assert result.success is False
    assert result.error_code == "MODEL_UNAVAILABLE"
    assert result.asset_ids == []
    assert assets.items == {}


def test_default_registry_requires_explicit_provider_configuration(monkeypatch) -> None:
    for name in (
        "AICF_TEXT_PROVIDER_ENDPOINT", "AICF_TEXT_PROVIDER_MODEL",
        "AICF_MEDIA_PROVIDER_ENDPOINT", "AICF_MEDIA_PROVIDER_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    registry = default_provider_registry()
    assert registry.ids() == []
