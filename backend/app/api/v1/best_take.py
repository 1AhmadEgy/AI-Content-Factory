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

    def project_for_shot(shot_id: str) -> str:
        with store._lock:
            row = store.connection.execute("SELECT e.project_id FROM shots s JOIN scenes sc ON sc.id=s.scene_id JOIN episodes e ON e.id=sc.episode_id WHERE s.id=?", (shot_id,)).fetchone()
        if row is None: raise HTTPException(status_code=404, detail="SHOT_NOT_FOUND")
        return row["project_id"]

    @router.get("/shots/{shot_id}/takes")
    def takes(shot_id: str, request: Request) -> dict:
        project_id = project_for_shot(shot_id)
        with store._lock: rows = store.connection.execute("SELECT * FROM shot_takes WHERE shot_id=? ORDER BY updated_at DESC, asset_id", (shot_id,)).fetchall()
        return {"data": [dict(row) for row in rows], "contextVersion": runtime.context_snapshot(project_id).get("contextVersion", 0), "requestId": request.state.request_id}

    @router.post("/shots/{shot_id}/select-take")
    def select_take(shot_id: str, body: SelectTakeRequest, request: Request) -> dict:
        project_id = project_for_shot(shot_id)
        asset = runtime.assets.get(body.assetId)
        if asset is None: raise HTTPException(status_code=404, detail="ASSET_NOT_FOUND")
        if asset.project_id != project_id: raise HTTPException(status_code=409, detail="ASSET_PROJECT_MISMATCH")
        if asset.status.value != "READY": raise HTTPException(status_code=422, detail="ASSET_NOT_READY")
        now = datetime.now(timezone.utc).isoformat()
        with store._lock, store.connection:
            store.connection.execute("UPDATE shot_takes SET selected=0, updated_at=? WHERE shot_id=?", (now, shot_id))
            store.connection.execute("INSERT INTO shot_takes(shot_id,asset_id,selected,reason,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(shot_id,asset_id) DO UPDATE SET selected=1,reason=excluded.reason,updated_at=excluded.updated_at", (shot_id, body.assetId, 1, body.reason, now))
        saved = runtime.series_bible.record_shot(project_id, shot_id, {"bestTakeAssetId": body.assetId, "bestTakeReason": body.reason, "bestTakeSelectedAt": now})
        return {"data": {"shotId": shot_id, "assetId": body.assetId, "selected": True, "reason": body.reason}, "contextVersion": saved["version"], "requestId": request.state.request_id}

    return router
