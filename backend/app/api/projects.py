from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from uuid import uuid4

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
        name = request.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="PROJECT_NAME_REQUIRED")
        project = Project(id=str(uuid4()), name=name)
        repository.create(project)
        return {"data": _serialize(project), "requestId": http_request.state.request_id}

    @router.get("")
    def list_projects(
        http_request: Request,
        page: int = Query(default=1, ge=1),
        pageSize: int = Query(default=50, ge=1, le=100),
    ) -> dict[str, object]:
        items, total = repository.list(page=page, page_size=pageSize)
        return {
            "data": {
                "items": [_serialize(project) for project in items],
                "pagination": {"page": page, "pageSize": pageSize, "total": total},
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
        name = request.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="PROJECT_NAME_REQUIRED")
        project = repository.update_name(project_id, name)
        if project is None:
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        return {"data": _serialize(project), "requestId": http_request.state.request_id}

    @router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_project(project_id: str) -> None:
        if not repository.delete(project_id):
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")

    return router
