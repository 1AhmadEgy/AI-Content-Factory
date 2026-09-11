from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from ...domain.assets import AssetStatus, AssetType
from ...domain.jobs import JobInput, JobType
from ...infrastructure.sqlite import SQLiteJobRepository
from ...orchestrator.job_service import JobService
from ...orchestrator.runtime import OrchestratorRuntime


class RenderOutput(BaseModel):
    container: str = "mp4"
    videoCodec: str = "h264"
    audioCodec: str = "aac"
    width: int = Field(default=1080, gt=0, le=7680)
    height: int = Field(default=1920, gt=0, le=7680)
    fps: int = Field(default=30, gt=0, le=120)


class SubtitleOptions(BaseModel):
    enabled: bool = True
    burnIn: bool = True


class BrandingOptions(BaseModel):
    enabled: bool = True
    brand: str = "afham-wadhak"
    introAssetId: str | None = None
    outroAssetId: str | None = None
    watermarkAssetId: str | None = None
    watermarkOpacity: float = Field(default=0.82, ge=0.0, le=1.0)


class RenderRequest(BaseModel):
    projectId: str
    timelineId: str
    output: RenderOutput = Field(default_factory=RenderOutput)
    subtitles: SubtitleOptions = Field(default_factory=SubtitleOptions)
    # None means: use the project's branding setting. An explicit value here
    # is a per-render override and does not change the project setting.
    branding: BrandingOptions | None = None


def _fingerprint(body: RenderRequest, effective_branding: BrandingOptions) -> str:
    payload = body.model_dump(mode="json")
    payload["branding"] = effective_branding.model_dump(mode="json")
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _resolve_branding(project, request_branding: BrandingOptions | None) -> BrandingOptions:
    if request_branding is not None:
        return request_branding

    settings = project.settings or {}
    configured = settings.get("branding") or {}
    return BrandingOptions(
        enabled=bool(configured.get("enabled", True)),
        brand=str(configured.get("brand") or "afham-wadhak"),
        introAssetId=configured.get("introAssetId"),
        outroAssetId=configured.get("outroAssetId"),
        watermarkAssetId=configured.get("watermarkAssetId"),
        watermarkOpacity=float(configured.get("watermarkOpacity", 0.82)),
    )


def build_router(runtime: OrchestratorRuntime, jobs: SQLiteJobRepository) -> APIRouter:
    router = APIRouter(prefix="/api/v1/render", tags=["render"])
    service = JobService(jobs)

    @router.post("", status_code=status.HTTP_202_ACCEPTED)
    def render(body: RenderRequest, request: Request, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> dict[str, Any]:
        if not idempotency_key:
            raise HTTPException(status_code=400, detail="IDEMPOTENCY_KEY_REQUIRED")
        project = runtime.repositories.projects.get(body.projectId)
        if project is None:
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        timeline_asset = runtime.assets.get(body.timelineId)
        if timeline_asset is None or timeline_asset.project_id != body.projectId:
            raise HTTPException(status_code=404, detail="TIMELINE_NOT_FOUND")
        if timeline_asset.type is not AssetType.DOCUMENT or timeline_asset.status is not AssetStatus.READY:
            raise HTTPException(status_code=422, detail="TIMELINE_NOT_READY")

        effective_branding = _resolve_branding(project, body.branding)
        operation = "POST:/api/v1/render"
        fingerprint = _fingerprint(body, effective_branding)
        existing = jobs.store.get_idempotency(idempotency_key, operation)
        if existing:
            if existing["request_fingerprint"] != fingerprint:
                raise HTTPException(status_code=409, detail="IDEMPOTENCY_CONFLICT")
            job = jobs.get(existing["resource_id"])
            if job is None:
                raise HTTPException(status_code=409, detail="IDEMPOTENCY_RESOURCE_MISSING")
            return {"data": {"jobId": job.id, "status": job.status.value}, "requestId": request.state.request_id, "idempotentReplay": True}

        job = service.create(
            project_id=body.projectId,
            job_type=JobType.RENDER,
            target_type="timeline",
            target_id=body.timelineId,
            priority=40,
            provider="ffmpeg",
            model=None,
            input=JobInput(
                parameters={
                    "output": body.output.model_dump(),
                    "subtitles": body.subtitles.model_dump(),
                    "branding": effective_branding.model_dump(),
                },
                reference_asset_ids=[body.timelineId],
            ),
        )
        if not jobs.store.claim_idempotency(idempotency_key, operation, fingerprint, job.id):
            raise HTTPException(status_code=409, detail="IDEMPOTENCY_CONFLICT")
        runtime.queue.enqueue(job)
        return {"data": {"jobId": job.id, "status": job.status.value}, "requestId": request.state.request_id}

    @router.get("/{render_job_id}")
    def get_render(render_job_id: str, request: Request) -> dict[str, Any]:
        job = jobs.get(render_job_id)
        if job is None or job.type is not JobType.RENDER:
            raise HTTPException(status_code=404, detail="RENDER_JOB_NOT_FOUND")
        return {"data": {"jobId": job.id, "status": job.status.value, "progress": job.progress, "output": job.output.asset_ids if job.output else None, "error": job.error_code}, "requestId": request.state.request_id}

    @router.post("/{render_job_id}/cancel")
    def cancel_render(render_job_id: str, request: Request) -> dict[str, Any]:
        job = jobs.get(render_job_id)
        if job is None or job.type is not JobType.RENDER:
            raise HTTPException(status_code=404, detail="RENDER_JOB_NOT_FOUND")
        runtime.workers.get("render").cancel(render_job_id)
        service.cancel(render_job_id)
        return {"data": {"jobId": render_job_id, "status": "CANCELLED"}, "requestId": request.state.request_id}

    return router
