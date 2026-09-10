from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from ...domain.content import ContentBrief
from ...domain.jobs import JobInput, JobType
from ...infrastructure.sqlite import SQLiteJobRepository, SQLiteProjectRepository
from ...orchestrator.job_service import JobService
from ...orchestrator.runtime import OrchestratorRuntime

router = APIRouter(prefix="/api/v1/factory", tags=["factory"])


class BriefRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="en", min_length=2, max_length=20)
    durationSeconds: int = Field(default=60, ge=15, le=86400)
    style: str = Field(default="documentary", min_length=1, max_length=100)
    audience: str = Field(default="general", min_length=1, max_length=200)
    platform: str = Field(default="youtube", min_length=1, max_length=50)
    aspectRatio: str = Field(default="16:9", pattern=r"^\d+:\d+$")


class StartFactoryRequest(BriefRequest):
    provider: str | None = None
    model: str | None = None


def _brief(request: BriefRequest) -> ContentBrief:
    return ContentBrief(
        topic=request.topic,
        language=request.language,
        duration_seconds=request.durationSeconds,
        style=request.style,
        audience=request.audience,
        platform=request.platform,
        aspect_ratio=request.aspectRatio,
    )


def _serialize_plan(plan: Any) -> dict[str, Any]:
    return {
        "title": plan.title,
        "logline": plan.logline,
        "synopsis": plan.synopsis,
        "scenes": [
            {
                "number": scene.number,
                "title": scene.title,
                "durationSeconds": scene.duration_seconds,
                "visual": scene.visual,
                "narration": scene.narration,
                "shots": [
                    {
                        "number": shot.number,
                        "prompt": shot.prompt,
                        "durationSeconds": shot.duration_seconds,
                        "camera": shot.camera,
                        "lighting": shot.lighting,
                        "style": shot.style,
                    }
                    for shot in scene.shots
                ],
            }
            for scene in plan.scenes
        ],
    }


def _fingerprint(request: StartFactoryRequest) -> str:
    canonical = json.dumps(request.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_router(
    projects: SQLiteProjectRepository,
    jobs: SQLiteJobRepository,
    runtime: OrchestratorRuntime,
) -> APIRouter:
    job_service = JobService(jobs)

    @router.post("/plan")
    def plan_factory(request: BriefRequest, http_request: Request) -> dict[str, Any]:
        plan = runtime.plan_content(_brief(request))
        return {
            "data": {"mode": "ai", "brief": request.model_dump(), "plan": _serialize_plan(plan)},
            "requestId": http_request.state.request_id,
        }

    @router.post("/projects/{project_id}/start", status_code=status.HTTP_202_ACCEPTED)
    def start_factory(
        project_id: str,
        request: StartFactoryRequest,
        http_request: Request,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> dict[str, Any]:
        if projects.get(project_id) is None:
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        if not idempotency_key:
            raise HTTPException(status_code=400, detail="IDEMPOTENCY_KEY_REQUIRED")

        operation = f"POST:/api/v1/factory/projects/{project_id}/start"
        fingerprint = _fingerprint(request)
        store = jobs.store
        existing = store.get_idempotency(idempotency_key, operation)
        if existing:
            if existing["request_fingerprint"] != fingerprint:
                raise HTTPException(status_code=409, detail="IDEMPOTENCY_CONFLICT")
            existing_job = jobs.get(existing["resource_id"])
            if existing_job is None:
                raise HTTPException(status_code=409, detail="IDEMPOTENCY_RESOURCE_MISSING")
            return {
                "data": {"projectId": project_id, "jobId": existing_job.id, "stage": existing_job.type.value, "status": existing_job.status.value},
                "requestId": http_request.state.request_id,
                "idempotentReplay": True,
            }

        brief = _brief(request)
        plan = runtime.plan_content(brief, request.model)
        job_input = JobInput(parameters={**request.model_dump(), "plan": _serialize_plan(plan)}, deterministic=request.model is None)
        job, existing_resource_id = job_service.create_with_idempotency(
            key=idempotency_key,
            operation=operation,
            fingerprint=fingerprint,
            project_id=project_id,
            job_type=JobType.STORY,
            target_type="project",
            target_id=project_id,
            priority=100,
            provider=request.provider or "mock",
            model=request.model or "mock-deterministic",
            input=job_input,
        )
        if existing_resource_id == "__IDEMPOTENCY_CONFLICT__":
            raise HTTPException(status_code=409, detail="IDEMPOTENCY_CONFLICT")
        if existing_resource_id:
            existing_job = jobs.get(existing_resource_id)
            if existing_job is None:
                raise HTTPException(status_code=409, detail="IDEMPOTENCY_RESOURCE_MISSING")
            return {
                "data": {"projectId": project_id, "jobId": existing_job.id, "stage": existing_job.type.value, "status": existing_job.status.value},
                "requestId": http_request.state.request_id,
                "idempotentReplay": True,
            }
        if job is None:
            raise HTTPException(status_code=500, detail="JOB_CREATION_FAILED")

        runtime.queue.enqueue(job)
        return {
            "data": {
                "projectId": project_id,
                "jobId": job.id,
                "stage": "STORY",
                "status": job.status.value,
                "plan": _serialize_plan(plan),
            },
            "requestId": http_request.state.request_id,
        }

    return router
