from backend.app.domain.assets import Asset, AssetProvenance, AssetStatus, AssetType, LicenseStatus
from backend.app.domain.jobs import GenerationJob, JobOutput, JobStatus, JobType
from backend.app.domain.projects import Project
from backend.app.domain.qc import QcResult
from backend.app.infrastructure.asset_repository import SQLiteAssetRepository
from backend.app.infrastructure.sqlite import SQLiteRepositories
from backend.app.infrastructure.storage import LocalAssetStorage
from backend.app.orchestrator.completion_gate import CompletionGate
from backend.app.orchestrator.job_service import JobService
from backend.app.orchestrator.runtime import OrchestratorRuntime

def test_worker_success_asset_provenance_qc_then_completed(tmp_path):
    repositories = SQLiteRepositories(":memory:"); project = Project("project-1", "Test"); repositories.projects.create(project); runtime = OrchestratorRuntime(repositories, tmp_path / "assets")
    job = JobService(repositories.jobs).create(project_id=project.id, job_type=JobType.IMAGE, target_type="shot", target_id="shot-1"); runtime.queue.enqueue(job); result = runtime.execute_next("mock")
    assert result is not None and result.status is JobStatus.COMPLETED
    persisted = repositories.jobs.get(job.id); assert persisted is not None and persisted.output is not None
    asset = runtime.assets.get(persisted.output.asset_ids[0]); assert asset is not None and asset.provenance.job_id == job.id and runtime.storage.verify(asset)
    repositories.close()

def test_qc_failure_blocks_completion(tmp_path):
    repositories = SQLiteRepositories(":memory:"); project = Project("project-1", "Test"); repositories.projects.create(project); storage = LocalAssetStorage(tmp_path / "assets"); assets = SQLiteAssetRepository(repositories.store)
    digest, path, size = storage.put_bytes(b"fixture")
    assets.create(Asset("asset-1", project.id, AssetType.IMAGE, path, "text/plain", size, digest, AssetStatus.READY, AssetProvenance(provider="mock", job_id="job-1", license_status=LicenseStatus.VERIFIED)))
    job = GenerationJob("job-1", project.id, JobType.IMAGE, "shot", status=JobStatus.RUNNING, attempt=1); job.output = JobOutput(["asset-1"])
    result = CompletionGate(assets, storage, lambda **kwargs: QcResult(asset_id=kwargs["asset_id"], passed=False, score=0.2)).check(job)
    assert result.allowed is False and result.code == "QC_BLOCKED" and result.qc_results[0].passed is False
    repositories.close()

def test_missing_or_invalid_output_is_blocked(tmp_path):
    repositories = SQLiteRepositories(":memory:"); project = Project("project-1", "Test"); repositories.projects.create(project); storage = LocalAssetStorage(tmp_path / "assets"); assets = SQLiteAssetRepository(repositories.store); gate = CompletionGate(assets, storage)
    missing = GenerationJob("job-missing", project.id, JobType.IMAGE, "shot", status=JobStatus.RUNNING, attempt=1); missing.output = JobOutput(["does-not-exist"]); result = gate.check(missing); assert result.allowed is False and result.code == "ASSET_NOT_PERSISTED"
    invalid = GenerationJob("job-invalid", project.id, JobType.IMAGE, "shot", status=JobStatus.RUNNING, attempt=1); invalid.output = JobOutput(["asset-invalid"]); digest, path, size = storage.put_bytes(b"valid")
    assets.create(Asset("asset-invalid", project.id, AssetType.IMAGE, path, "text/plain", size + 1, digest, AssetStatus.READY, AssetProvenance(provider="mock", job_id=invalid.id, license_status=LicenseStatus.VERIFIED)))
    result = gate.check(invalid); assert result.allowed is False and result.code == "QC_BLOCKED" and result.qc_results[0].blocked
    repositories.close()
