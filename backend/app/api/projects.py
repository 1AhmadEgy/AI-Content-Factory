from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ..domain.projects import Project
from ..infrastructure.sqlite import SQLiteProjectRepository
from ..library.country_catalog import get_country_languages, get_country_library


DEFAULT_COUNTRY_ID = "egypt"


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10000)
    settings: dict = Field(default_factory=dict)


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    settings: dict | None = None


def _country_settings(settings: dict) -> dict:
    """Normalize project localization settings without inventing country content."""
    value = dict(settings or {})
    country_id = str(value.get("countryId") or DEFAULT_COUNTRY_ID).strip().lower()
    country = get_country_library(country_id)
    if country is None:
        raise HTTPException(status_code=404, detail="COUNTRY_LIBRARY_NOT_FOUND")

    languages = get_country_languages(country_id)
    allowed = {item["id"] for item in languages}
    source = str(value.get("sourceLanguage") or country["defaultLanguage"])
    if source not in allowed:
        raise HTTPException(status_code=400, detail="LANGUAGE_NOT_SUPPORTED_BY_COUNTRY")

    raw_targets = value.get("targetLanguages")
    targets = list(dict.fromkeys(raw_targets if isinstance(raw_targets, list) else [source]))
    if any(str(item) not in allowed for item in targets):
        raise HTTPException(status_code=400, detail="LANGUAGE_NOT_SUPPORTED_BY_COUNTRY")

    dialect = value.get("dialect") or country["locale"]
    value.update(
        {
            "countryId": country_id,
            "libraryId": country["libraryId"],
            "sourceLanguage": source,
            "targetLanguages": [str(item) for item in targets],
            "dialect": str(dialect),
            "translationPolicy": {
                "preserveSource": True,
                "manualOverridesWin": True,
                "immutableVersions": True,
                **dict(value.get("translationPolicy") or {}),
            },
            "glossary": dict(value.get("glossary") or {}),
            "translationVersions": dict(value.get("translationVersions") or {}),
        }
    )
    return value


def _serialize(project: Project) -> dict:
    return {"id": project.id, "name": project.name, "description": project.description, "settings": project.settings, "createdAt": project.created_at.isoformat(), "updatedAt": project.updated_at.isoformat()}


def build_router(repository: SQLiteProjectRepository) -> APIRouter:
    router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

    @router.post("", status_code=status.HTTP_201_CREATED)
    def create_project(request: CreateProjectRequest, http_request: Request):
        settings = _country_settings(request.settings)
        project = Project(id=str(uuid4()), name=request.name, description=request.description, settings=settings)
        repository.create(project)
        return {"data": _serialize(project), "requestId": http_request.state.request_id}

    @router.get("")
    def list_projects(http_request: Request, page: int = Query(default=1, ge=1), pageSize: int = Query(default=50, ge=1, le=200)):
        items = repository.list(); start = (page - 1) * pageSize; page_items = items[start:start + pageSize]
        return {"data": [_serialize(p) for p in page_items], "pagination": {"page": page, "pageSize": pageSize, "total": len(items), "hasNext": start + pageSize < len(items)}, "requestId": http_request.state.request_id}

    @router.get("/{project_id}")
    def get_project(project_id: str, http_request: Request):
        project = repository.get(project_id)
        if project is None: raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        return {"data": _serialize(project), "requestId": http_request.state.request_id}

    @router.patch("/{project_id}")
    def update_project(project_id: str, request: UpdateProjectRequest, http_request: Request):
        project = repository.get(project_id)
        if project is None: raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        if request.name is not None: project.name = request.name
        if request.description is not None: project.description = request.description
        if request.settings is not None: project.settings = _country_settings(request.settings)
        else: project.settings = _country_settings(project.settings)
        project.updated_at = datetime.now(timezone.utc)
        repository.update(project)
        return {"data": _serialize(project), "requestId": http_request.state.request_id}

    @router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_project(project_id: str):
        if repository.get(project_id) is None: raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        repository.delete(project_id)
        return None

    return router
