from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..domain.projects import Project
from ..infrastructure.sqlite import SQLiteProjectRepository


class CreateProjectRequest(BaseModel):
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
    def create_project(request: CreateProjectRequest) -> dict[str, dict[str, str]]:
        project = Project(id=str(uuid4()), name=request.name)
        repository.create(project)
        return {"data": _serialize(project)}

    @router.get("/{project_id}")
    def get_project(project_id: str) -> dict[str, dict[str, str]]:
        project = repository.get(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        return {"data": _serialize(project)}

    return router
