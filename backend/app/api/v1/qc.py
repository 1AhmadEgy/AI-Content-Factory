from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from ...domain.jobs import JobInput, JobType
from ...infrastructure.sqlite import SQLiteJobRepository
from ...orchestrator.job_service import JobService
from ...orchestrator.runtime import OrchestratorRuntime


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


def build_router(runtime: OrchestratorRuntime, jobs: SQLiteJobRepository) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["qc"])
    store = jobs.store
    with store._lock, store.connection:
        store.connection.execute("CREATE TABLE IF NOT EXISTS qc_reviews (id TEXT PRIMARY KEY, asset_id TEXT NOT NULL, status TEXT NOT NULL, reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        store.connection.execute("CREATE INDEX IF NOT EXISTS idx_qc_reviews_asset ON qc_reviews(asset_id, created_at DESC)")
    service = JobService(jobs, context_provider=runtime.context_snapshot)

    def project_for_asset(asset_id: str) -> str:
        asset = runtime.assets.get(asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="ASSET_NOT_FOUND")
        return asset.project_id

    @router.get("/qc/{qc_id}")
    def get_qc(qc_id: str, request: Request) -> dict:
        row = store._get("qc_reviews", qc_id)
        if row is None:
            raise HTTPException(status_code=404, detail="QC_NOT_FOUND")
        return {"data": dict(row), "requestId": request.state.request_id}

    @router.get("/assets/{asset_id}/qc")
    def asset_qc(asset_id: str, request: Request) -> dict:
        project_for_asset(asset_id)
        with store._lock:
            rows = store.connection.execute("SELECT * FROM qc_reviews WHERE asset_id=? ORDER BY created_at DESC", (asset_id,)).fetchall()
        return {"data": [dict(row) for row in rows], "requestId": request.state.request_id}

    @router.post("/assets/{asset_id}/qc", status_code=status.HTTP_202_ACCEPTED)
    def run_qc(asset_id: str, request: Request) -> dict:
        project_id = project_for_asset(asset_id)
        job = service.create(project_id=project_id, job_type=JobType.QC, target_type="asset", target_id=asset_id, priority=60, provider="local", model=None, input=JobInput(reference_asset_ids=[asset_id]))
        runtime.queue.enqueue(job)
        return {"data": {"jobId": job.id, "status": job.status.value, "contextVersion": job.input.parameters.get("contextVersion", 0)}, "requestId": request.state.request_id}

    @router.post("/qc/{qc_id}/approve")
    def approve(qc_id: str, request: Request) -> dict:
        row = store._get("qc_reviews", qc_id)
        if row is None:
            raise HTTPException(status_code=404, detail="QC_NOT_FOUND")
        now = datetime.now(timezone.utc).isoformat()
        store._insert("UPDATE qc_reviews SET status='APPROVED', updated_at=? WHERE id=?", (now, qc_id))
        project_id = project_for_asset(row["asset_id"])
        saved = runtime.series_bible.record_job(project_id, {"jobId": None, "type": "QC_REVIEW", "targetType": "asset", "targetId": row["asset_id"], "status": "APPROVED", "reviewId": qc_id, "reviewedAt": now})
        return {"data": {"id": qc_id, "status": "APPROVED"}, "contextVersion": saved["version"], "requestId": request.state.request_id}

    @router.post("/qc/{qc_id}/reject")
    def reject(qc_id: str, body: RejectRequest, request: Request) -> dict:
        row = store._get("qc_reviews", qc_id)
        if row is None:
            raise HTTPException(status_code=404, detail="QC_NOT_FOUND")
        now = datetime.now(timezone.utc).isoformat()
        store._insert("UPDATE qc_reviews SET status='REJECTED', reason=?, updated_at=? WHERE id=?", (body.reason, now, qc_id))
        project_id = project_for_asset(row["asset_id"])
        saved = runtime.series_bible.record_job(project_id, {"jobId": None, "type": "QC_REVIEW", "targetType": "asset", "targetId": row["asset_id"], "status": "REJECTED", "reason": body.reason, "reviewId": qc_id, "reviewedAt": now})
        return {"data": {"id": qc_id, "status": "REJECTED", "reason": body.reason}, "contextVersion": saved["version"], "requestId": request.state.request_id}

    return router
