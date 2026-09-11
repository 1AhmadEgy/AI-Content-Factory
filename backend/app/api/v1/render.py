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
    branding: BrandingOptions = Field(default_factory=BrandingOptions)


def _fingerprint(body: RenderRequest) -> str:
    return hashlib.sha256(json.dumps(body.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_router(runtime: OrchestratorRuntime, jobs: SQLiteJobRepository) -> APIRouter:
    router = APIRouter(prefix="/api/v1/render", tags=["render"])
    service = JobService(jobs)

    @router.post("", status_code=status.HTTP_202_ACCEPTED)
    def render(body: RenderRequest, request: Request, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> dict[str, Any]:
        if not idempotency_key:
            raise HTTPException(status_code=400, detail="IDEMPOTENCY_KEY_REQUIRED")
        if runtime.repositories.projects.get(body.projectId) is None:
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        timeline_asset = runtime.assets.get(body.timelineId)
        if timeline_asset is None or timeline_asset.project_id != body.projectId:
            raise HTTPException(status_code=404, detail="TIMELINE_NOT_FOUND")
        if timeline_asset.type is not AssetType.DOCUMENT or timeline_asset.status is not AssetStatus.READY:
            raise HTTPException(status_code=422, detail="TIMELINE_NOT_READY")

        operation = "POST:/api/v1/render"
        fingerprint = _fingerprint(body)
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
                    "branding": body.branding.model_dump(),
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
