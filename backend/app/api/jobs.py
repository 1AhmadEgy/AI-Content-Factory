from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request, status
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
    return {"id": job.id, "parentJobId": job.parent_job_id, "projectId": job.project_id, "type": job.type.value, "targetType": job.target_type, "targetId": job.target_id, "priority": job.priority, "status": job.status.value, "progress": job.progress, "attempt": job.attempt, "maxAttempts": job.max_attempts, "provider": job.provider, "model": job.model, "input": {"schemaVersion": "1.0", "parameters": job.input.parameters, "referenceAssetIds": job.input.reference_asset_ids, "constraints": job.input.constraints, "seed": job.input.seed, "deterministic": job.input.deterministic}, "output": None if job.output is None else {"schemaVersion": "1.0", "assetIds": job.output.asset_ids, "metrics": job.output.metrics, "providerRunId": job.output.provider_run_id}, "errorCode": job.error_code, "errorMessage": job.error_message, "createdAt": job.created_at.isoformat(), "startedAt": job.started_at.isoformat() if job.started_at else None, "completedAt": job.completed_at.isoformat() if job.completed_at else None, "updatedAt": job.updated_at.isoformat()}


def _serialize_event(event: JobEvent) -> dict[str, Any]:
    return {"id": event.id, "jobId": event.job_id, "projectId": event.project_id, "eventType": event.event_type, "status": event.status, "progress": event.progress, "payload": event.payload, "createdAt": event.created_at.isoformat()}


def _fingerprint(request: CreateJobRequest) -> str:
    payload = request.model_dump(mode="json")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_router(repository: SQLiteJobRepository, runtime: OrchestratorRuntime | None = None, events: SQLiteJobEventRepository | None = None) -> APIRouter:
    service = JobService(repository)
    event_repository = events or (SQLiteJobEventRepository(runtime.repositories.store) if runtime else None)

    @router.get("")
    def list_jobs(
        request: Request,
        project_id: str | None = Query(default=None, alias="projectId"),
        job_status: str | None = Query(default=None, alias="status"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        """Read-only Control Center feed. Never exposes raw database rows."""
        clauses: list[str] = []
        params: list[Any] = []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if job_status:
            clauses.append("status = ?")
            params.append(job_status.upper())
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = repository.store.connection.execute(
            f"SELECT * FROM jobs{where} ORDER BY created_at DESC LIMIT ?", (*params, limit)
        ).fetchall()
        jobs = [repository._job_from_row(row) if hasattr(repository, "_job_from_row") else None for row in rows]
        # Keep reconstruction in the repository boundary when possible; this
        # fallback uses the same canonical serializer source through get().
        data = [_serialize(repository.get(row["id"])) for row in rows]
        return {"data": data, "meta": {"count": len(data), "limit": limit}, "requestId": request.state.request_id}

    @router.post("", status_code=status.HTTP_202_ACCEPTED)
    def create_job(request: CreateJobRequest, http_request: Request, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")) -> dict[str, Any]:
        if not idempotency_key: raise HTTPException(status_code=400, detail="IDEMPOTENCY_KEY_REQUIRED")
        fingerprint = _fingerprint(request)
        store = repository.store
        existing = store.get_idempotency(idempotency_key, "POST:/api/v1/jobs")
        if existing:
            if existing["request_fingerprint"] != fingerprint: raise HTTPException(status_code=409, detail="IDEMPOTENCY_CONFLICT")
            existing_job = repository.get(existing["resource_id"])
            if existing_job is None: raise HTTPException(status_code=409, detail="IDEMPOTENCY_RESOURCE_MISSING")
            return {"data": _serialize(existing_job), "requestId": http_request.state.request_id, "idempotentReplay": True}
        job = service.create(project_id=request.projectId, job_type=request.type, target_type=request.targetType, target_id=request.targetId, parent_job_id=request.parentJobId, priority=request.priority, max_attempts=request.maxAttempts, provider=request.provider, model=request.model, input=JobInput(parameters=request.input.parameters, reference_asset_ids=request.input.referenceAssetIds, constraints=request.input.constraints, seed=request.input.seed, deterministic=request.input.deterministic))
        claimed = store.claim_idempotency(idempotency_key, "POST:/api/v1/jobs", fingerprint, job.id)
        if not claimed:
            existing = store.get_idempotency(idempotency_key, "POST:/api/v1/jobs")
            if existing and existing["request_fingerprint"] == fingerprint:
                existing_job = repository.get(existing["resource_id"])
                if existing_job: return {"data": _serialize(existing_job), "requestId": http_request.state.request_id, "idempotentReplay": True}
            raise HTTPException(status_code=409, detail="IDEMPOTENCY_CONFLICT")
        if runtime: runtime.queue.enqueue(job)
        return {"data": _serialize(job), "requestId": http_request.state.request_id}

    @router.get("/{job_id}")
    def get_job(job_id: str, request: Request) -> dict[str, Any]:
        job = repository.get(job_id)
        if job is None: raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
        return {"data": _serialize(job), "requestId": request.state.request_id}

    @router.post("/{job_id}/cancel")
    def cancel_job(job_id: str, request: Request) -> dict[str, Any]:
        try: job = service.cancel(job_id)
        except KeyError as exc: raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
        return {"data": _serialize(job), "requestId": request.state.request_id}

    @router.post("/{job_id}/execute", status_code=status.HTTP_200_OK)
    def execute_job(job_id: str, request: Request) -> dict[str, Any]:
        if runtime is None: raise HTTPException(status_code=503, detail="ORCHESTRATOR_NOT_CONFIGURED")
        job = repository.get(job_id)
        if job is None: raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
        result = runtime.execute_next("mock")
        if result is None or result.job.id != job_id: raise HTTPException(status_code=409, detail="JOB_NOT_NEXT_RUNNABLE")
        return {"data": _serialize(result.job), "execution": {"status": result.status.value, "retried": result.retried}, "requestId": request.state.request_id}

    @router.post("/{job_id}/heartbeat")
    def heartbeat_job(job_id: str, request: Request, lease_id: str = Header(..., alias="X-Lease-Id"), worker_id: str = Header(..., alias="X-Worker-Id")) -> dict[str, Any]:
        if runtime is None: raise HTTPException(status_code=503, detail="ORCHESTRATOR_NOT_CONFIGURED")
        try: runtime.heartbeat(job_id, lease_id, worker_id)
        except KeyError as exc: raise HTTPException(status_code=404 if str(exc.args[0]) == "JOB_NOT_FOUND" else 409, detail=str(exc.args[0])) from exc
        return {"data": {"jobId": job_id, "workerId": worker_id, "leaseId": lease_id, "status": "HEARTBEAT_ACCEPTED"}, "requestId": request.state.request_id}

    @router.post("/maintenance/recover-expired")
    def recover_expired(request: Request) -> dict[str, Any]:
        if runtime is None: raise HTTPException(status_code=503, detail="ORCHESTRATOR_NOT_CONFIGURED")
        return {"data": {"recovered": runtime.recover_expired()}, "requestId": request.state.request_id}

    @router.get("/{job_id}/events")
    def get_job_events(job_id: str, request: Request, limit: int = 200) -> dict[str, Any]:
        if repository.get(job_id) is None: raise HTTPException(status_code=404, detail="JOB_NOT_FOUND")
        if event_repository is None: return {"data": [], "requestId": request.state.request_id}
        return {"data": [_serialize_event(event) for event in event_repository.list_for_job(job_id, max(1, min(limit, 500)))], "requestId": request.state.request_id}

    return router
