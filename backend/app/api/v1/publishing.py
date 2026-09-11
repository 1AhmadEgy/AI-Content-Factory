from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from ...domain.assets import AssetStatus, AssetType, LicenseStatus
from ...domain.jobs import JobInput, JobType
from ...infrastructure.sqlite import SQLiteJobRepository
from ...orchestrator.job_service import JobService
from ...orchestrator.runtime import OrchestratorRuntime


class PublishRequest(BaseModel):
    projectId: str = Field(min_length=1)
    assetId: str = Field(min_length=1)
    platforms: list[str] = Field(min_length=1)
    title: str = Field(default="AI Content", min_length=1, max_length=500)
    description: str = Field(default="", max_length=10000)
    tags: list[str] = Field(default_factory=list)
    language: str = Field(default="en", min_length=2, max_length=20)
    scheduledAt: str | None = None


def _fingerprint(body: PublishRequest) -> str:
    value = json.dumps(body.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(value.encode()).hexdigest()


def build_router(runtime: OrchestratorRuntime, jobs: SQLiteJobRepository) -> APIRouter:
    router = APIRouter(prefix="/api/v1/publish", tags=["publishing"])
    service = JobService(jobs, context_provider=runtime.context_snapshot)

    @router.get("/providers")
    def providers(request: Request) -> dict[str, Any]:
        return {"data": [{"id": name, "name": runtime.workers.get("publish").adapters.get(name).name} for name in runtime.workers.get("publish").adapters.names()], "requestId": request.state.request_id}

    @router.post("", status_code=status.HTTP_202_ACCEPTED)
    def publish(body: PublishRequest, request: Request, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> dict[str, Any]:
        if not idempotency_key:
            raise HTTPException(status_code=400, detail="IDEMPOTENCY_KEY_REQUIRED")
        if runtime.repositories.projects.get(body.projectId) is None:
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        asset = runtime.assets.get(body.assetId)
        if asset is None or asset.project_id != body.projectId:
            raise HTTPException(status_code=404, detail="ASSET_NOT_FOUND")
        if asset.type is not AssetType.VIDEO:
            raise HTTPException(status_code=422, detail="PUBLISH_ASSET_NOT_VIDEO")
        if asset.status is not AssetStatus.READY:
            raise HTTPException(status_code=422, detail="PUBLISH_ASSET_NOT_READY")
        if asset.provenance.license_status is not LicenseStatus.VERIFIED:
            raise HTTPException(status_code=422, detail="PUBLISH_LICENSE_NOT_VERIFIED")
        if not body.platforms:
            raise HTTPException(status_code=400, detail="PUBLISH_PLATFORMS_REQUIRED")
        platforms = list(dict.fromkeys(platform.strip().lower() for platform in body.platforms if platform.strip()))
        if not platforms:
            raise HTTPException(status_code=400, detail="PUBLISH_PLATFORMS_REQUIRED")
        available = set(runtime.workers.get("publish").adapters.names())
        unsupported = [platform for platform in platforms if platform not in available]
        if unsupported:
            raise HTTPException(status_code=422, detail={"code": "PUBLISH_ADAPTER_NOT_FOUND", "platforms": unsupported})
        operation = "POST:/api/v1/publish"
        fingerprint = _fingerprint(body.model_copy(update={"platforms": platforms}))
        existing = jobs.store.get_idempotency(idempotency_key, operation)
        if existing:
            if existing["request_fingerprint"] != fingerprint:
                raise HTTPException(status_code=409, detail="IDEMPOTENCY_CONFLICT")
            job = jobs.get(existing["resource_id"])
            if job is None:
                raise HTTPException(status_code=409, detail="IDEMPOTENCY_RESOURCE_MISSING")
            return {"data": {"jobId": job.id, "projectId": job.project_id, "assetId": body.assetId, "status": job.status.value, "contextVersion": job.input.parameters.get("contextVersion", 0)}, "requestId": request.state.request_id, "idempotentReplay": True}
        job = service.create(
            project_id=body.projectId,
            job_type=JobType.PUBLISH,
            target_type="asset",
            target_id=body.assetId,
            priority=50,
            provider="platform-adapters",
            model=None,
            input=JobInput(
                parameters={"platforms": platforms, "title": body.title, "description": body.description, "tags": body.tags, "language": body.language, "scheduledAt": body.scheduledAt},
                reference_asset_ids=[body.assetId],
            ),
        )
        if not jobs.store.claim_idempotency(idempotency_key, operation, fingerprint, job.id):
            raise HTTPException(status_code=409, detail="IDEMPOTENCY_CONFLICT")
        runtime.queue.enqueue(job)
        return {"data": {"jobId": job.id, "projectId": job.projectId if hasattr(job, "projectId") else job.project_id, "assetId": body.assetId, "status": job.status.value, "contextVersion": job.input.parameters.get("contextVersion", 0)}, "requestId": request.state.request_id}

    @router.get("/{publish_job_id}")
    def get_publish(publish_job_id: str, request: Request) -> dict[str, Any]:
        job = jobs.get(publish_job_id)
        if job is None or job.type is not JobType.PUBLISH:
            raise HTTPException(status_code=404, detail="PUBLISH_JOB_NOT_FOUND")
        return {"data": {"jobId": job.id, "projectId": job.project_id, "assetId": job.target_id, "status": job.status.value, "progress": job.progress, "output": job.output.asset_ids if job.output else None, "metrics": job.output.metrics if job.output else None, "error": job.error_code, "errorMessage": job.error_message, "contextVersion": job.input.parameters.get("contextVersion", 0)}, "requestId": request.state.request_id}

    @router.post("/{publish_job_id}/cancel")
    def cancel_publish(publish_job_id: str, request: Request) -> dict[str, Any]:
        job = jobs.get(publish_job_id)
        if job is None or job.type is not JobType.PUBLISH:
            raise HTTPException(status_code=404, detail="PUBLISH_JOB_NOT_FOUND")
        runtime.queue.cancel(publish_job_id)
        job = jobs.get(publish_job_id)
        return {"data": {"jobId": publish_job_id, "status": job.status.value if job else "CANCELLED"}, "requestId": request.state.request_id}

    return router
