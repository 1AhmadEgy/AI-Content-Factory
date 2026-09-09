from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..domain.job_events import JobEvent
from ..domain.jobs import GenerationJob, JobInput, JobType
from ..infrastructure.job_event_repository import SQLiteJobEventRepository
from ..infrastructure.sqlite import SQLiteJobRepository
from ..orchestrator.job_service import JobService
from ..orchestrator.runtime import OrchestratorRuntime


router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


class JobInputRequest(BaseModel):
    parameters: dict[str, Any] = Field(default_factory=dict)
    referenceAssetIds: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    seed: int | None = None
    deterministic: bool = False


class CreateJobRequest(BaseModel):
    projectId: str
    type: JobType
    targetType: str
    targetId: str | None = None
    parentJobId: str | None = None
    priority: int = 100
    maxAttempts: int = Field(default=3, ge=1, le=20)
    provider: str | None = None
    model: str | None = None
    input: JobInputRequest = Field(default_factory=JobInputRequest)


def _serialize(job: GenerationJob) -> dict[str, Any]:
    return {
        "id": job.id, "parentJobId": job.parent_job_id, "projectId": job.project_id,
        "type": job.type.value, "targetType": job.target_type, "targetId": job.target_id,
        "priority": job.priority, "status": job.status.value, "progress": job.progress,
        "attempt": job.attempt, "maxAttempts": job.max_attempts, "provider": job.provider,
        "model": job.model,
        "input": {"schemaVersion": "1.0", "parameters": job.input.parameters,
                   "referenceAssetIds": job.input.reference_asset_ids, "constraints": job.input.constraints,
                   "seed": job.input.seed, "deterministic": job.input.deterministic},
        "output": None if job.output is None else {"schemaVersion": "1.0", "assetIds": job.output.asset_ids,
                   "metrics": job.output.metrics, "providerRunId": job.output.provider_run_id},
        "errorCode": job.error_code, "errorMessage": job.error_message,
        "createdAt": job.created_at.isoformat(), "startedAt": job.started_at.isoformat() if job.started_at else None,
        "completedAt": job.completed_at.isoformat() if job.completed_at else None, "updatedAt": job.updated_at.isoformat(),
    }


def _serialize_event(event: JobEvent) -> dict[str, Any]:
    return {"id": event.id, "jobId": event.job_id, "projectId": event.project_id,
            "eventType": event.event_type, "status": event.status, "progress": event.progress,
            "payload": event.payload, "createdAt": event.created_at.isoformat()}


def build_router(repository: SQLiteJobRepository, runtime: OrchestratorRuntime | None = None, events: SQLiteJobEventRepository | None = None) -> APIRouter:
    service = JobService(repository)
    event_repository = events or SQLiteJobEventRepository(runtime.repositories.store) if runtime else events

    @router.post("", status_code=status.HTTP_202_ACCEPTED)
    def create_job(request: CreateJobRequest) -> dict[str, Any]:
        job = service.create(
            project_id=request.projectId, job_type=request.type, target_type=request.targetType,
            target_id=request.targetId, parent_job_id=request.parentJobId, priority=request.priority,
            max_attempts=request.maxAttempts, provider=request.provider, model=request.model,
            input=JobInput(parameters=request.input.parameters, reference_asset_ids=request.input.referenceAssetIds,
                           constraints=request.input.constraints, seed=request.input.seed,
                           deterministic=request.input.deterministic),
        )
        if runtime:
            runtime.queue.enqueue(job)
        return {"data": _serialize(job)}

    @router.get("/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        job = repository.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
        return {"data": _serialize(job)}

    @router.post("/{job_id}/execute", status_code=status.HTTP_200_OK)
    def execute_job(job_id: str) -> dict[str, Any]:
        if runtime is None:
            raise HTTPException(status_code=503, detail="ORCHESTRATOR_NOT_CONFIGURED")
        job = repository.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
        result = runtime.execute_next("mock")
        if result is None or result.job.id != job_id:
            raise HTTPException(status_code=409, detail="JOB_NOT_NEXT_RUNNABLE")
        return {"data": _serialize(result.job), "execution": {"status": result.status.value, "retried": result.retried}}

    @router.get("/{job_id}/events")
    def get_job_events(job_id: str, limit: int = 200) -> dict[str, Any]:
        if repository.get(job_id) is None:
            raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
        if event_repository is None:
            return {"data": []}
        return {"data": [_serialize_event(event) for event in event_repository.list_for_job(job_id, limit)]}

    return router
