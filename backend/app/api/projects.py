from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ..domain.projects import Project
from ..infrastructure.sqlite import SQLiteProjectRepository


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class UpdateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


def _serialize(project: Project) -> dict[str, str]:
    return {
        "id": project.id,
        "name": project.name,
        "createdAt": project.created_at.isoformat(),
        "updatedAt": project.updated_at.isoformat(),
    }


def build_router(repository: SQLiteProjectRepository) -> APIRouter:
    router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    def create_project(request: CreateProjectRequest, http_request: Request) -> dict[str, object]:
        project = Project(id=str(uuid4()), name=request.name.strip())
        if not project.name:
            raise HTTPException(status_code=400, detail="PROJECT_NAME_REQUIRED")
        repository.create(project)
        return {"data": _serialize(project), "requestId": http_request.state.request_id}

    @router.get("")
    def list_projects(
        http_request: Request,
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, object]:
        items, total = repository.list(limit=limit, offset=offset)
        return {
            "data": {
                "items": [_serialize(project) for project in items],
                "pagination": {"limit": limit, "offset": offset, "total": total},
            },
            "requestId": http_request.state.request_id,
        }

    @router.get("/{project_id}")
    def get_project(project_id: str, http_request: Request) -> dict[str, object]:
        project = repository.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        return {"data": _serialize(project), "requestId": http_request.state.request_id}

    @router.patch("/{project_id}")
    def update_project(project_id: str, request: UpdateProjectRequest, http_request: Request) -> dict[str, object]:
        project = repository.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        project.name = request.name.strip()
        project.updated_at = datetime.now(timezone.utc)
        if not project.name:
            raise HTTPException(status_code=400, detail="PROJECT_NAME_REQUIRED")
        repository.update(project)
        return {"data": _serialize(project), "requestId": http_request.state.request_id}

    @router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_project(project_id: str) -> None:
        if repository.get(project_id) is None:
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        repository.delete(project_id)

    return router
