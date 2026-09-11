from pathlib import Path

from backend.app.domain.assets import AssetType
from backend.app.domain.jobs import GenerationJob, JobInput, JobStatus, JobType
from backend.app.infrastructure.storage import LocalAssetStorage
from backend.app.providers.contracts import ModelAdapter, ModelCapability, ProviderResponse
from backend.app.providers.registry import ModelRegistry, RegisteredModel, default_provider_registry
from backend.app.workers.provider_worker import ProviderGenerationWorker


class AssetStore:
    def __init__(self): self.items = {}
    def create(self, asset): self.items[asset.id] = asset; return asset
    def get(self, asset_id): return self.items.get(asset_id)


class ResponseAdapter(ModelAdapter):
    def __init__(self, response: ProviderResponse):
        self.response = response

    def capability(self) -> ModelCapability:
        return ModelCapability(category="generation", capabilities=frozenset({"image", "video", "tts"}), runtime="TEST")

    def health_check(self) -> bool:
        return True

    def execute(self, request):
        return self.response

    def cancel(self, provider_run_id: str) -> bool:
        return False


def _job(job_id: str = "image-1", job_type: JobType = JobType.IMAGE) -> GenerationJob:
    return GenerationJob(
        id=job_id,
        project_id="project-1",
        type=job_type,
        target_type="shot",
        target_id="shot-1",
        status=JobStatus.RUNNING,
        input=JobInput(parameters={"prompt": "cinematic city"}, seed=42),
    )


def _worker(tmp_path: Path, response: ProviderResponse, assets: AssetStore | None = None) -> tuple[ProviderGenerationWorker, AssetStore]:
    asset_store = assets or AssetStore()
    registry = ModelRegistry()
    registry.register(RegisteredModel("test-image", "test-provider", ResponseAdapter(response)))
    worker = ProviderGenerationWorker(registry, LocalAssetStorage(tmp_path), asset_store)
    worker.initialize()
    return worker, asset_store


def _context():
    return type("Context", (), {"cancellation_requested": False})()


def test_provider_generation_worker_does_not_succeed_without_real_provider(tmp_path: Path) -> None:
    assets = AssetStore()
    worker = ProviderGenerationWorker(ModelRegistry(), LocalAssetStorage(tmp_path), assets)
    worker.initialize()
    result = worker.execute(_job(), _context())
    assert result.success is False
    assert result.error_code == "MODEL_UNAVAILABLE"
    assert result.asset_ids == []
    assert assets.items == {}


def test_provider_success_without_provider_run_id_is_rejected(tmp_path: Path) -> None:
    worker, assets = _worker(
        tmp_path,
        ProviderResponse(success=True, output_bytes=b"real-output", output_mime_type="image/png"),
    )
    result = worker.execute(_job(), _context())
    assert result.success is False
    assert result.error_code == "PROVIDER_RUN_ID_MISSING"
    assert assets.items == {}


def test_provider_success_with_real_output_and_run_id_persists_asset(tmp_path: Path) -> None:
    worker, assets = _worker(
        tmp_path,
        ProviderResponse(success=True, output_bytes=b"real-output", output_mime_type="image/png", provider_run_id="provider-run-1"),
    )
    result = worker.execute(_job(), _context())
    assert result.success is True
    assert result.provider_run_id == "provider-run-1"
    assert len(result.asset_ids) == 1
    asset = assets.items[result.asset_ids[0]]
    assert asset.project_id == "project-1"
    assert asset.type == AssetType.IMAGE
    assert asset.size_bytes == len(b"real-output")
    assert asset.provenance.license_status.value == "VERIFIED"
    assert Path(asset.path).read_bytes() == b"real-output"


def test_provider_rejects_binary_output_without_mime_type(tmp_path: Path) -> None:
    worker, assets = _worker(
        tmp_path,
        ProviderResponse(success=True, output_bytes=b"real-output", provider_run_id="provider-run-1"),
    )
    result = worker.execute(_job(), _context())
    assert result.success is False
    assert result.error_code == "PROVIDER_MIME_TYPE_MISSING"
    assert assets.items == {}


def test_provider_rejects_binary_output_with_wrong_mime_type(tmp_path: Path) -> None:
    worker, assets = _worker(
        tmp_path,
        ProviderResponse(success=True, output_bytes=b"real-output", output_mime_type="video/mp4", provider_run_id="provider-run-1"),
    )
    result = worker.execute(_job(), _context())
    assert result.success is False
    assert result.error_code == "PROVIDER_MIME_TYPE_MISMATCH"
    assert assets.items == {}


def test_provider_accepts_video_mime_for_video_job(tmp_path: Path) -> None:
    worker, assets = _worker(
        tmp_path,
        ProviderResponse(success=True, output_bytes=b"real-video", output_mime_type="video/mp4", provider_run_id="provider-run-video"),
    )
    result = worker.execute(_job("video-1", JobType.VIDEO), _context())
    assert result.success is True
    asset = assets.items[result.asset_ids[0]]
    assert asset.type == AssetType.VIDEO
    assert asset.mime_type == "video/mp4"


def test_provider_rejects_audio_mime_for_lipsync_job(tmp_path: Path) -> None:
    worker, assets = _worker(
        tmp_path,
        ProviderResponse(success=True, output_bytes=b"real-lipsync", output_mime_type="audio/wav", provider_run_id="provider-run-lipsync"),
    )
    result = worker.execute(_job("lipsync-1", JobType.LIPSYNC), _context())
    assert result.success is False
    assert result.error_code == "PROVIDER_MIME_TYPE_MISMATCH"
    assert assets.items == {}


def test_provider_accepts_video_mime_for_lipsync_job(tmp_path: Path) -> None:
    worker, assets = _worker(
        tmp_path,
        ProviderResponse(success=True, output_bytes=b"real-lipsync", output_mime_type="video/mp4", provider_run_id="provider-run-lipsync"),
    )
    result = worker.execute(_job("lipsync-1", JobType.LIPSYNC), _context())
    assert result.success is True
    asset = assets.items[result.asset_ids[0]]
    assert asset.type == AssetType.VIDEO
    assert asset.mime_type == "video/mp4"


def test_provider_rejects_referenced_asset_that_does_not_exist(tmp_path: Path) -> None:
    worker, assets = _worker(
        tmp_path,
        ProviderResponse(success=True, output_asset_ids=["missing"], provider_run_id="provider-run-1"),
    )
    result = worker.execute(_job(), _context())
    assert result.success is False
    assert result.error_code == "PROVIDER_ASSET_NOT_FOUND"
    assert assets.items == {}


def test_default_registry_requires_explicit_provider_configuration(monkeypatch) -> None:
    for name in (
        "AICF_TEXT_PROVIDER_ENDPOINT", "AICF_TEXT_PROVIDER_MODEL",
        "AICF_MEDIA_PROVIDER_ENDPOINT", "AICF_MEDIA_PROVIDER_MODEL",
        "HF_TOKEN", "HF_MODEL", "HF_MEDIA_TOKEN", "HF_MEDIA_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    registry = default_provider_registry()
    assert registry.ids() == []


def test_default_registry_registers_real_huggingface_media_task(monkeypatch) -> None:
    for name in (
        "AICF_TEXT_PROVIDER_ENDPOINT", "AICF_TEXT_PROVIDER_MODEL",
        "AICF_MEDIA_PROVIDER_ENDPOINT", "AICF_MEDIA_PROVIDER_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HF_MEDIA_TOKEN", "hf-test")
    monkeypatch.setenv("HF_MEDIA_MODEL", "black-forest-labs/FLUX.1-schnell")
    monkeypatch.setenv("HF_MEDIA_TASK", "text-to-image")
    registry = default_provider_registry()
    assert registry.ids() == ["huggingface-media:black-forest-labs/FLUX.1-schnell"]
    registered = registry.get("huggingface-media:black-forest-labs/FLUX.1-schnell")
    assert registered.adapter.capability().capabilities == frozenset({"image"})
