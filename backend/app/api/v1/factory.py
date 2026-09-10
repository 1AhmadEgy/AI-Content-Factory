from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from ...application.content_planner import DeterministicContentPlanner
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
    aspectRatio: str = Field(default="16:9", pattern=r"^\\d+:\\d+$")


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


def build_router(
    projects: SQLiteProjectRepository,
    jobs: SQLiteJobRepository,
    runtime: OrchestratorRuntime,
) -> APIRouter:
    job_service = JobService(jobs)
    planner = DeterministicContentPlanner()

    @router.post("/plan")
    def plan_factory(request: BriefRequest, http_request: Request) -> dict[str, Any]:
        plan = planner.plan(_brief(request))
        return {
            "data": {"mode": "mock", "brief": request.model_dump(), "plan": _serialize_plan(plan)},
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

        plan = planner.plan(_brief(request))
        job = job_service.create(
            project_id=project_id,
            job_type=JobType.STORY,
            target_type="project",
            target_id=project_id,
            priority=100,
            provider=request.provider or "mock",
            model=request.model or "deterministic-content-planner-v1",
            input=JobInput(
                parameters={
                    "topic": request.topic,
                    "language": request.language,
                    "durationSeconds": request.durationSeconds,
                    "style": request.style,
                    "audience": request.audience,
                    "platform": request.platform,
                    "aspectRatio": request.aspectRatio,
                    "plan": _serialize_plan(plan),
                },
                deterministic=True,
            ),
        )
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
