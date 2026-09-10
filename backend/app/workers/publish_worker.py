from __future__ import annotations

import json
import uuid

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext
from ..publishing.adapters import AdapterRegistry, PublishRequest


class PublishWorker(Worker):
    """Prepare provider-neutral publication packages through platform adapters."""

    worker_type = "publish"

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository, adapters: AdapterRegistry | None = None) -> None:
        self.storage, self.assets = storage, assets
        self.adapters = adapters or AdapterRegistry()
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        asset = next((self.assets.get(a) for a in job.input.reference_asset_ids if self.assets.get(a) is not None), None)
        if asset is None or asset.status is not AssetStatus.READY:
            return JobExecutionResult(False, error_code="PUBLISH_ASSET_NOT_READY", error_message="No ready asset to publish")
        platforms = [str(p).lower() for p in job.input.parameters.get("platforms", ["youtube", "tiktok", "instagram", "facebook"])]
        title = str(job.input.parameters.get("title", "AI Content"))
        description = str(job.input.parameters.get("description", ""))
        tags = [str(t) for t in job.input.parameters.get("tags", [])]
        scheduled_at = job.input.parameters.get("scheduledAt")
        packages = []
        for platform in platforms:
            adapter = self.adapters.get(platform)
            request = PublishRequest(asset_path=asset.path, title=title, description=description, scheduled_at=str(scheduled_at) if scheduled_at else None, metadata={"tags": ",".join(tags), "language": str(job.input.parameters.get("language", "en"))})
            errors = adapter.validate(request)
            prepared = adapter.publish(request) if not errors else None
            packages.append({"platform": platform, "adapter": adapter.name, "status": prepared.status if prepared else "FAILED", "error": ";".join(errors) if errors else None, "payload": dict(prepared.payload or {}) if prepared and prepared.payload else {}})
        package = {"jobId": job.id, "projectId": job.project_id, "assetIds": list(job.input.reference_asset_ids), "platforms": packages, "title": title, "description": description, "tags": tags, "status": "READY_FOR_EXTERNAL_PUBLISH"}
        payload = (json.dumps(package, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        digest, path, size = self.storage.put_bytes(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"publish:{job.id}:{digest}"))
        self.assets.create(Asset(asset_id, job.project_id, AssetType.DOCUMENT, path, "application/json; charset=utf-8", size, digest, AssetStatus.READY, build_provenance(job, source_asset_ids=list(job.input.reference_asset_ids), metadata={"publicationPackage": True, "adapterCount": len(platforms)}, license_status=LicenseStatus.VERIFIED)))
        return JobExecutionResult(True, [asset_id], {"platformCount": len(platforms), "status": "READY_FOR_EXTERNAL_PUBLISH"}, f"publish-{job.id}")

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
