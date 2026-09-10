from __future__ import annotations

import json
import uuid

from ..domain.asset_repositories import AssetRepository
from ..domain.assets import Asset, AssetStatus, AssetType, LicenseStatus
from ..domain.jobs import GenerationJob, JobInput, JobType
from ..domain.repositories import JobRepository
from ..infrastructure.storage import LocalAssetStorage
from ..orchestrator.job_service import JobService
from ..orchestrator.provenance import build_provenance
from ..orchestrator.queue import JobExecutionResult, JobQueue, Worker, WorkerContext


class BatchWorker(Worker):
    """Expand one persisted BATCH job into bounded, independently retryable jobs."""

    worker_type = "batch"
    MAX_ITEMS = 100

    def __init__(self, storage: LocalAssetStorage, assets: AssetRepository, jobs: JobRepository, queue: JobQueue) -> None:
        self.storage, self.assets, self.jobs, self.queue = storage, assets, jobs, queue
        self._initialized = False

    def initialize(self) -> None:
        self._initialized = True

    def health_check(self) -> bool:
        return self._initialized

    def execute(self, job: GenerationJob, context: WorkerContext) -> JobExecutionResult:
        if not self._initialized:
            return JobExecutionResult(False, error_code="WORKER_NOT_INITIALIZED", error_message="Worker is not initialized")
        if job.type is not JobType.BATCH:
            return JobExecutionResult(False, error_code="UNSUPPORTED_JOB_TYPE", error_message=job.type.value)

        items = job.input.parameters.get("items", [])
        if not isinstance(items, list) or not items:
            return JobExecutionResult(False, error_code="BATCH_ITEMS_REQUIRED", error_message="items must be a non-empty array")
        if len(items) > self.MAX_ITEMS:
            return JobExecutionResult(False, error_code="BATCH_TOO_LARGE", error_message=f"maximum batch size is {self.MAX_ITEMS}")

        service = JobService(self.jobs)
        child_ids: list[str] = []
        for index, item in enumerate(items, 1):
            if not isinstance(item, dict):
                return JobExecutionResult(False, error_code="INVALID_BATCH_ITEM", error_message=f"item {index} must be an object")
            raw_type = str(item.get("type", "STORY")).upper()
            try:
                child_type = JobType(raw_type)
            except ValueError:
                return JobExecutionResult(False, error_code="INVALID_BATCH_JOB_TYPE", error_message=raw_type)
            if child_type is JobType.BATCH:
                return JobExecutionResult(False, error_code="NESTED_BATCH_NOT_ALLOWED", error_message="BATCH jobs cannot contain BATCH jobs")
            params = item.get("parameters", {})
            if not isinstance(params, dict):
                return JobExecutionResult(False, error_code="INVALID_BATCH_PARAMETERS", error_message=f"item {index} parameters must be an object")
            child = service.create(
                project_id=job.project_id,
                job_type=child_type,
                target_type=str(item.get("targetType", child_type.value.lower())),
                target_id=str(item["targetId"]) if item.get("targetId") is not None else None,
                parent_job_id=job.id,
                priority=int(item.get("priority", job.priority)),
                max_attempts=int(item.get("maxAttempts", job.max_attempts)),
                provider=str(item["provider"]) if item.get("provider") else job.provider,
                model=str(item["model"]) if item.get("model") else job.model,
                input=JobInput(
                    parameters=params,
                    reference_asset_ids=[str(x) for x in item.get("referenceAssetIds", [])],
                    constraints=item.get("constraints", {}) if isinstance(item.get("constraints", {}), dict) else {},
                    seed=item.get("seed"),
                    deterministic=bool(item.get("deterministic", job.input.deterministic)),
                ),
            )
            self.queue.enqueue(child)
            child_ids.append(child.id)
            context.report_progress(index / len(items), "batch_expand")

        plan = {"batchJobId": job.id, "projectId": job.project_id, "childJobIds": child_ids, "count": len(child_ids)}
        payload = (json.dumps(plan, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
        digest, path, size = self.storage.put_bytes(payload)
        asset_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"batch:{job.id}:{digest}"))
        self.assets.create(
            Asset(asset_id, job.project_id, AssetType.DOCUMENT, path, "application/json; charset=utf-8", size, digest, AssetStatus.READY,
                  build_provenance(job, metadata={"batchExpansion": True, "childJobIds": child_ids}, license_status=LicenseStatus.VERIFIED))
        )
        return JobExecutionResult(True, [asset_id], {"count": len(child_ids), "childJobIds": child_ids}, f"batch-{job.id}")

    def cancel(self, job_id: str) -> None:
        return None

    def shutdown(self) -> None:
        self._initialized = False
