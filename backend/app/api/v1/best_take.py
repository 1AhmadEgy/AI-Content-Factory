from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...infrastructure.sqlite import SQLiteJobRepository
from ...orchestrator.runtime import OrchestratorRuntime


class SelectTakeRequest(BaseModel):
    assetId: str = Field(min_length=1)
    reason: str = Field(default="manual_selection", max_length=1000)


def build_router(runtime: OrchestratorRuntime, jobs: SQLiteJobRepository) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["best-take"])
    store = jobs.store
    with store._lock, store.connection:
        store.connection.execute("CREATE TABLE IF NOT EXISTS shot_takes (shot_id TEXT NOT NULL, asset_id TEXT NOT NULL, selected INTEGER NOT NULL DEFAULT 0, reason TEXT, updated_at TEXT NOT NULL, PRIMARY KEY (shot_id, asset_id))")

    @router.get("/shots/{shot_id}/takes")
    def takes(shot_id: str, request: Request) -> dict:
        with store._lock:
            rows = store.connection.execute("SELECT * FROM shot_takes WHERE shot_id=? ORDER BY updated_at DESC, asset_id", (shot_id,)).fetchall()
        return {"data": [dict(row) for row in rows], "requestId": request.state.request_id}

    @router.post("/shots/{shot_id}/select-take")
    def select_take(shot_id: str, body: SelectTakeRequest, request: Request) -> dict:
        asset = runtime.assets.get(body.assetId)
        if asset is None:
            raise HTTPException(status_code=404, detail="ASSET_NOT_FOUND")
        if asset.status.value != "READY":
            raise HTTPException(status_code=422, detail="ASSET_NOT_READY")
        now = datetime.now(timezone.utc).isoformat()
        with store._lock, store.connection:
            store.connection.execute("UPDATE shot_takes SET selected=0, updated_at=? WHERE shot_id=?", (now, shot_id))
            store.connection.execute("INSERT INTO shot_takes(shot_id,asset_id,selected,reason,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(shot_id,asset_id) DO UPDATE SET selected=1,reason=excluded.reason,updated_at=excluded.updated_at", (shot_id, body.assetId, 1, body.reason, now))
        return {"data": {"shotId": shot_id, "assetId": body.assetId, "selected": True, "reason": body.reason}, "requestId": request.state.request_id}

    return router
