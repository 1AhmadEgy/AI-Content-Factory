from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...orchestrator.runtime import OrchestratorRuntime


class SeriesBibleWrite(BaseModel):
    series: dict[str, Any] = Field(default_factory=dict)
    rules: list[str] = Field(default_factory=list)


class ContinuityWrite(BaseModel):
    continuity: dict[str, Any] = Field(default_factory=dict)


def build_router(runtime: OrchestratorRuntime) -> APIRouter:
    router = APIRouter(prefix="/api/v1/projects/{project_id}/series-bible", tags=["series-bible"])

    def ensure_project(project_id: str) -> None:
        if runtime.repositories.projects.get(project_id) is None:
            raise HTTPException(404, "PROJECT_NOT_FOUND")

    @router.get("")
    def get_bible(project_id: str, request: Request):
        ensure_project(project_id)
        current = runtime.context.get(project_id)
        return {"data": runtime.series_bible.snapshot(project_id), "version": current["version"], "requestId": request.state.request_id}

    @router.put("")
    def initialize_or_update(project_id: str, body: SeriesBibleWrite, request: Request):
        ensure_project(project_id)
        saved = runtime.series_bible.initialize(project_id, body.series, body.rules)
        return {"data": runtime.series_bible.snapshot(project_id), "version": saved["version"], "requestId": request.state.request_id}

    @router.patch("/continuity")
    def update_continuity(project_id: str, body: ContinuityWrite, request: Request):
        ensure_project(project_id)
        saved = runtime.series_bible.update_continuity(project_id, body.continuity)
        return {"data": runtime.series_bible.snapshot(project_id), "version": saved["version"], "requestId": request.state.request_id}

    @router.get("/events")
    def events(project_id: str, request: Request, limit: int = 100):
        ensure_project(project_id)
        if limit < 1 or limit > 500:
            raise HTTPException(400, "INVALID_LIMIT")
        return {"data": runtime.context.events(project_id, limit=limit), "requestId": request.state.request_id}

    return router
