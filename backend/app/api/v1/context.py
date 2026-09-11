from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...infrastructure.sqlite import SQLiteProjectRepository
from ...services.project_context import ProjectContextStore


class ContextWrite(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)
    replace: bool = False
    eventType: str = Field(default="context.updated", min_length=1, max_length=100)
    entityType: str | None = None
    entityId: str | None = None


class ContextEvent(BaseModel):
    eventType: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    entityType: str | None = None
    entityId: str | None = None


def build_router(projects: SQLiteProjectRepository, contexts: ProjectContextStore) -> APIRouter:
    router = APIRouter(prefix="/api/v1/projects/{project_id}/context", tags=["context"])

    def _require_project(project_id: str) -> None:
        if projects.get(project_id) is None:
            raise HTTPException(404, "PROJECT_NOT_FOUND")

    @router.get("")
    def get_context(project_id: str, request: Request):
        _require_project(project_id)
        return {"data": contexts.get(project_id), "requestId": request.state.request_id}

    @router.put("")
    def save_context(project_id: str, body: ContextWrite, request: Request):
        _require_project(project_id)
        result = contexts.save(project_id, body.context, event_type=body.eventType, entity_type=body.entityType, entity_id=body.entityId) if body.replace else contexts.merge(project_id, body.context, event_type=body.eventType, entity_type=body.entityType, entity_id=body.entityId)
        return {"data": result, "requestId": request.state.request_id}

    @router.post("/events")
    def append_context_event(project_id: str, body: ContextEvent, request: Request):
        _require_project(project_id)
        result = contexts.merge(project_id, {"lastEvent": {"type": body.eventType, "payload": body.payload}}, event_type=body.eventType, entity_type=body.entityType, entity_id=body.entityId)
        return {"data": result, "requestId": request.state.request_id}

    @router.get("/events")
    def get_context_events(project_id: str, request: Request, limit: int = 100):
        _require_project(project_id)
        return {"data": contexts.events(project_id, limit), "requestId": request.state.request_id}

    return router
