from __future__ import annotations

import json
import uuid
from pathlib import Path

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, Worker, WorkerContext
from ..publishing.adapters import AdapterRegistry, PublishRequest


class PublishWorker(Worker):
    """Publish only through concrete adapters that return an external id."""

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
        if not job.input.reference_asset_ids:
            return JobExecutionResult(False, error_code="PUBLISH_ASSET_REQUIRED", error_message="At least one source asset is required")

        asset = next((self.assets.get(asset_id) for asset_id in job.input.reference_asset_ids), None)
        if asset is None:
            return JobExecutionResult(False, error_code="PUBLISH_ASSET_NOT_FOUND", error_message="No source asset was found")
        if asset.project_id != job.project_id:
            return JobExecutionResult(False, error_code="PUBLISH_ASSET_PROJECT_MISMATCH", error_message=asset.id)
        if asset.type is not AssetType.VIDEO:
            return JobExecutionResult(False, error_code="PUBLISH_ASSET_NOT_VIDEO", error_message="Publication requires a video source")
        if asset.status is not AssetStatus.READY:
            return JobExecutionResult(False, error_code="PUBLISH_ASSET_NOT_READY", error_message="Source asset is not ready")
        if asset.provenance.license_status is not LicenseStatus.VERIFIED:
            return JobExecutionResult(False, error_code="PUBLISH_LICENSE_NOT_VERIFIED", error_message=asset.id)
        if not Path(asset.path).is_file():
            return JobExecutionResult(False, error_code="PUBLISH_ASSET_MISSING", error_message=asset.path, retryable=True)
        if not self.storage.verify(asset):
            return JobExecutionResult(False, error_code="PUBLISH_ASSET_INTEGRITY_FAILED", error_message=asset.id, retryable=True)

        raw_platforms = job.input.parameters.get("platforms", [])
        if not isinstance(raw_platforms, (list, tuple)):
            return JobExecutionResult(False, error_code="PUBLISH_PLATFORMS_INVALID", error_message="platforms must be a list")
        platforms = list(dict.fromkeys(str(platform).lower().strip() for platform in raw_platforms if str(platform).strip()))
        if not platforms:
            return JobExecutionResult(False, error_code="PUBLISH_PLATFORMS_REQUIRED", error_message="At least one platform is required")

        title = str(job.input.parameters.get("title", "AI Content"))
        description = str(job.input.parameters.get("description", ""))
        raw_tags = job.input.parameters.get("tags", [])
        if not isinstance(raw_tags, (list, tuple)):
            return JobExecutionResult(False, error_code="PUBLISH_TAGS_INVALID", error_message="tags must be a list")
        tags = [str(tag) for tag in raw_tags]
        scheduled_at = job.input.parameters.get("scheduledAt")
        packages: list[dict[str, object]] = []
        failures: list[str] = []

        for index, platform in enumerate(platforms):
            context.report_progress(index / len(platforms), f"publish:{platform}:validate")
            try:
                adapter = self.adapters.get(platform)
            except KeyError:
                failures.append(platform)
                packages.append({"platform": platform, "adapter": None, "status": "FAILED", "error": "PUBLISH_ADAPTER_NOT_FOUND", "externalId": None, "payload": {}})
                continue
            request = PublishRequest(asset_path=asset.path, title=title, description=description, scheduled_at=str(scheduled_at) if scheduled_at else None, metadata={"tags": ",".join(tags), "language": str(job.input.parameters.get("language", "en"))})
            errors = adapter.validate(request)
            if errors:
                failures.append(platform)
                packages.append({"platform": platform, "adapter": adapter.name, "status": "FAILED", "error": ";".join(errors), "externalId": None, "payload": {}})
                continue
            prepared = adapter.schedule(request) if scheduled_at else adapter.publish(request)
            status = prepared.status
            if status not in {"PUBLISHED", "SCHEDULED"} or not prepared.external_id:
                failures.append(platform)
                error = prepared.error or "PUBLISH_EXTERNAL_ID_REQUIRED"
                status = "FAILED"
            else:
                error = None
            packages.append({"platform": platform, "adapter": adapter.name, "status": status, "externalId": prepared.external_id, "error": error, "payload": dict(prepared.payload or {})})
            context.report_progress((index + 1) / len(platforms), f"publish:{platform}:complete")

        package_status = "FAILED" if len(failures) == len(platforms) else ("PARTIAL" if failures else "PUBLISHED")
        package = {"jobId": job.id, "projectId": job.project_id, "assetIds": list(job.input.reference_asset_ids), "sourceAssetId": asset.id, "platforms": packages, "title": title, "description": description, "tags": tags, "scheduledAt": scheduled_at, "status": package_status}
        payload = (json.dumps(package, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        digest, path, size = self.storage.put_bytes(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"publish:{job.id}:{digest}"))
        provenance = build_provenance(job, source_asset_ids=[asset.id], metadata={"provider": "aicf-publisher", "model": "publication-package", "publicationPackage": True, "adapterCount": len(platforms), "status": package_status, "failureCount": len(failures)}, license_status=LicenseStatus.VERIFIED)
        self.assets.create(Asset(asset_id, job.project_id, AssetType.DOCUMENT, path, "application/json; charset=utf-8", size, digest, AssetStatus.READY, provenance))
        context.report_progress(1.0, "publish:complete")
        if failures:
            return JobExecutionResult(False, [asset_id], {"platformCount": len(platforms), "failedPlatforms": failures, "status": package_status}, f"publish-{job.id}", error_code="PUBLISH_FAILED", error_message=",".join(failures), retryable=False)
        return JobExecutionResult(True, [asset_id], {"platformCount": len(platforms), "status": package_status}, f"publish-{job.id}")

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
