from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from ...domain.jobs import JobInput, JobType
from ...infrastructure.sqlite import SQLiteJobRepository
from ...orchestrator.job_service import JobService
from ...orchestrator.runtime import OrchestratorRuntime


RESOURCE_TYPES = {"series", "episode", "story", "character", "world", "location", "scene", "shot", "dialogue", "voice", "timeline"}
JOB_TYPES = {"story": JobType.STORY, "character": JobType.CHARACTER, "world": JobType.WORLD, "scene": JobType.SCENE, "shot": JobType.SHOT, "dialogue": JobType.TTS, "voice": JobType.TTS, "timeline": JobType.TIMELINE}


class ResourceRequest(BaseModel):
    projectId: str | None = None
    parentId: str | None = None
    title: str = Field(default="Untitled", min_length=1, max_length=500)
    description: str = Field(default="", max_length=10000)
    data: dict[str, Any] = Field(default_factory=dict)


class PatchResourceRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    data: dict[str, Any] | None = None
    parentId: str | None = None


def build_router(runtime: OrchestratorRuntime, jobs: SQLiteJobRepository) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["content"])
    store = jobs.store
    with store._lock, store.connection:
        store.connection.execute("CREATE TABLE IF NOT EXISTS content_resources (id TEXT PRIMARY KEY, resource_type TEXT NOT NULL, project_id TEXT, parent_id TEXT, title TEXT NOT NULL, description TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        store.connection.execute("CREATE INDEX IF NOT EXISTS idx_content_type_parent ON content_resources(resource_type,parent_id,created_at)")
        store.connection.execute("CREATE INDEX IF NOT EXISTS idx_content_project ON content_resources(project_id,resource_type)")
    service = JobService(jobs)

    def row_to_dict(row) -> dict[str, Any]:
        return {"id": row["id"], "type": row["resource_type"], "projectId": row["project_id"], "parentId": row["parent_id"], "title": row["title"], "description": row["description"], "data": json.loads(row["payload_json"]), "createdAt": row["created_at"], "updatedAt": row["updated_at"]}

    def ensure_type(resource_type: str) -> str:
        value = resource_type.lower()
        if value not in RESOURCE_TYPES:
            raise HTTPException(status_code=404, detail="RESOURCE_TYPE_NOT_FOUND")
        return value

    def get_row(resource_id: str):
        row = store._get("content_resources", resource_id)
        if row is None:
            raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
        return row

    def create(resource_type: str, body: ResourceRequest, request: Request) -> dict:
        resource_type = ensure_type(resource_type)
        if resource_type in {"series", "episode", "scene", "shot"} and not body.parentId and resource_type != "series":
            raise HTTPException(status_code=400, detail="PARENT_ID_REQUIRED")
        if resource_type == "series" and not body.projectId:
            raise HTTPException(status_code=400, detail="PROJECT_ID_REQUIRED")
        if body.projectId and runtime.repositories.projects.get(body.projectId) is None:
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
        resource_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with store._lock, store.connection:
            store.connection.execute("INSERT INTO content_resources VALUES(?,?,?,?,?,?,?,?,?)", (resource_id, resource_type, body.projectId, body.parentId, body.title, body.description, json.dumps(body.data, ensure_ascii=False, sort_keys=True), now, now))
        return {"data": {"id": resource_id, "type": resource_type, "projectId": body.projectId, "parentId": body.parentId, "title": body.title, "description": body.description, "data": body.data, "createdAt": now, "updatedAt": now}, "requestId": request.state.request_id}

    @router.post("/{resource_type}", status_code=status.HTTP_201_CREATED)
    def create_resource(resource_type: str, body: ResourceRequest, request: Request):
        return create(resource_type, body, request)

    @router.get("/{resource_type}")
    def list_resources(resource_type: str, request: Request, projectId: str | None = Query(default=None), parentId: str | None = Query(default=None), page: int = Query(default=1, ge=1), pageSize: int = Query(default=50, ge=1, le=200)):
        resource_type = ensure_type(resource_type)
        sql = "SELECT * FROM content_resources WHERE resource_type=?"; args: list[Any] = [resource_type]
        if projectId: sql += " AND project_id=?"; args.append(projectId)
        if parentId: sql += " AND parent_id=?"; args.append(parentId)
        sql += " ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?"; args.extend([pageSize, (page - 1) * pageSize])
        with store._lock:
            rows = store.connection.execute(sql, tuple(args)).fetchall()
        return {"data": [row_to_dict(r) for r in rows], "pagination": {"page": page, "pageSize": pageSize, "total": len(rows), "hasNext": len(rows) == pageSize}, "requestId": request.state.request_id}

    @router.get("/{resource_type}/{resource_id}")
    def get_resource(resource_type: str, resource_id: str, request: Request):
        resource_type = ensure_type(resource_type)
        row = get_row(resource_id)
        if row["resource_type"] != resource_type:
            raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
        return {"data": row_to_dict(row), "requestId": request.state.request_id}

    @router.patch("/{resource_type}/{resource_id}")
    def patch_resource(resource_type: str, resource_id: str, body: PatchResourceRequest, request: Request):
        resource_type = ensure_type(resource_type); row = get_row(resource_id)
        if row["resource_type"] != resource_type: raise HTTPException(status_code=404, detail="RESOURCE_NOT_FOUND")
        now = datetime.now(timezone.utc).isoformat(); title = body.title if body.title is not None else row["title"]; desc = body.description if body.description is not None else row["description"]; parent = body.parentId if body.parentId is not None else row["parent_id"]; payload = body.data if body.data is not None else json.loads(row["payload_json"])
        store._insert("UPDATE content_resources SET parent_id=?,title=?,description=?,payload_json=?,updated_at=? WHERE id=?", (parent, title, desc, json.dumps(payload, ensure_ascii=False, sort_keys=True), now, resource_id))
        return {"data": row_to_dict(get_row(resource_id)), "requestId": request.state.request_id}

    @router.post("/{resource_type}/{resource_id}/generate", status_code=status.HTTP_202_ACCEPTED)
    def generate(resource_type: str, resource_id: str, request: Request):
        resource_type = ensure_type(resource_type); row = get_row(resource_id)
        if row["resource_type"] != resource_type or resource_type not in JOB_TYPES: raise HTTPException(status_code=422, detail="GENERATION_NOT_SUPPORTED")
        project_id = row["project_id"]
        if not project_id:
            raise HTTPException(status_code=400, detail="PROJECT_ID_REQUIRED")
        job = service.create(project_id=project_id, job_type=JOB_TYPES[resource_type], target_type=resource_type, target_id=resource_id, priority=50, provider="auto", model=None, input=JobInput(parameters={"resourceId": resource_id, "resourceType": resource_type, "payload": json.loads(row["payload_json"])}))
        runtime.queue.enqueue(job)
        return {"data": {"jobId": job.id, "status": job.status.value}, "requestId": request.state.request_id}

    @router.post("/shots/{shot_id}/regenerate", status_code=status.HTTP_202_ACCEPTED)
    def regenerate_shot(shot_id: str, request: Request):
        return generate("shot", shot_id, request)

    @router.post("/episodes/{episode_id}/story", status_code=status.HTTP_202_ACCEPTED)
    def create_story_for_episode(episode_id: str, body: ResourceRequest, request: Request):
        row = get_row(episode_id)
        if row["resource_type"] != "episode": raise HTTPException(status_code=404, detail="EPISODE_NOT_FOUND")
        body.projectId = row["project_id"]; body.parentId = episode_id
        created = create("story", body, request); story_id = created["data"]["id"]
        return generate("story", story_id, request)

    @router.post("/dialogues/{dialogue_id}/synthesize", status_code=status.HTTP_202_ACCEPTED)
    def synthesize(dialogue_id: str, request: Request):
        return generate("dialogue", dialogue_id, request)

    return router
