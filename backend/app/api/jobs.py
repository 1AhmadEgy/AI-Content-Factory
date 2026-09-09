from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..domain.jobs import GenerationJob, JobInput, JobType
from ..orchestrator.job_service import JobService
from ..infrastructure.sqlite import SQLiteJobRepository


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
        "id": job.id,
        "parentJobId": job.parent_job_id,
        "projectId": job.project_id,
        "type": job.type.value,
        "targetType": job.target_type,
        "targetId": job.target_id,
        "priority": job.priority,
        "status": job.status.value,
        "progress": job.progress,
        "attempt": job.attempt,
        "maxAttempts": job.max_attempts,
        "provider": job.provider,
        "model": job.model,
        "input": {
            "schemaVersion": "1.0",
            "parameters": job.input.parameters,
            "referenceAssetIds": job.input.reference_asset_ids,
            "constraints": job.input.constraints,
            "seed": job.input.seed,
            "deterministic": job.input.deterministic,
        },
        "output": None if job.output is None else {
            "schemaVersion": "1.0",
            "assetIds": job.output.asset_ids,
            "metrics": job.output.metrics,
            "providerRunId": job.output.provider_run_id,
        },
        "errorCode": job.error_code,
        "errorMessage": job.error_message,
        "createdAt": job.created_at.isoformat(),
        "startedAt": job.started_at.isoformat() if job.started_at else None,
        "completedAt": job.completed_at.isoformat() if job.completed_at else None,
        "updatedAt": job.updated_at.isoformat(),
    }


def build_router(repository: SQLiteJobRepository) -> APIRouter:
    service = JobService(repository)

    @router.post("", status_code=status.HTTP_202_ACCEPTED)
    def create_job(request: CreateJobRequest) -> dict[str, Any]:
        job = service.create(
            project_id=request.projectId,
            job_type=request.type,
            target_type=request.targetType,
            target_id=request.targetId,
            parent_job_id=request.parentJobId,
            priority=request.priority,
            max_attempts=request.maxAttempts,
            provider=request.provider,
            model=request.model,
            job_input=JobInput(
                parameters=request.input.parameters,
                reference_asset_ids=request.input.referenceAssetIds,
                constraints=request.input.constraints,
                seed=request.input.seed,
                deterministic=request.input.deterministic,
            ),
        )
        return {"data": _serialize(job)}

    @router.get("/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        job = repository.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
        return {"data": _serialize(job)}

    return router
