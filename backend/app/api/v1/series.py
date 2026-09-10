from __future__ import annotations

from copy import deepcopy
from typing import Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...library.series_templates import get_series_template, list_series_templates
from ...library.continuity import build_episode_context, merge_series_defaults, new_series_context
from ...infrastructure.series_context_repository import SQLiteSeriesContextRepository


class ApplyTemplateRequest(BaseModel):
    templateId: str = Field(min_length=1, max_length=100)
    title: str | None = Field(default=None, max_length=500)


class ContextPatchRequest(BaseModel):
    context: dict[str, Any]


def build_router(runtime) -> APIRouter:
    router = APIRouter(prefix="/api/v1/series", tags=["series"])
    repo = SQLiteSeriesContextRepository(runtime.repositories.store)

    def project_or_404(project_id: str):
        project = runtime.repositories.projects.get(project_id)
        if project is None:
            raise HTTPException(404, "PROJECT_NOT_FOUND")
        return project

    @router.get("/templates")
    def templates(request: Request):
        return {"data": list_series_templates(), "requestId": request.state.request_id}

    @router.get("/templates/{template_id}")
    def template(template_id: str, request: Request):
        value = get_series_template(template_id)
        if value is None:
            raise HTTPException(404, "SERIES_TEMPLATE_NOT_FOUND")
        return {"data": value, "requestId": request.state.request_id}

    @router.post("/projects/{project_id}/apply-template")
    def apply_template(project_id: str, body: ApplyTemplateRequest, request: Request):
        project_or_404(project_id)
        template = get_series_template(body.templateId)
        if template is None:
            raise HTTPException(404, "SERIES_TEMPLATE_NOT_FOUND")
        defaults = template.get("defaults", {})
        current = repo.get(project_id)
        if current is None:
            context = new_series_context(
                series_id=project_id,
                title=body.title or template["name"],
                template_id=body.templateId,
                genre=template.get("genre", ""),
                character_ids=list(defaults.get("characterIds", [])),
                location_ids=list(defaults.get("locationIds", [])),
            )
            context = merge_series_defaults(
                context,
                character_ids=list(defaults.get("characterIds", [])),
                location_ids=list(defaults.get("locationIds", [])),
                rules=dict(template.get("continuity", {})),
            )
            context["template"] = deepcopy(template)
        else:
            context = current
            context["templateId"] = context.get("templateId") or body.templateId
            context["genre"] = context.get("genre") or template.get("genre", "")
            context = merge_series_defaults(
                context,
                character_ids=list(defaults.get("characterIds", [])),
                location_ids=list(defaults.get("locationIds", [])),
                rules=dict(template.get("continuity", {})),
            )
        if body.title:
            context["title"] = body.title
        repo.save(project_id, context)
        return {"data": context, "requestId": request.state.request_id}

    @router.get("/projects/{project_id}/context")
    def get_context(project_id: str, request: Request):
        project_or_404(project_id)
        context = repo.get(project_id)
        if context is None:
            raise HTTPException(404, "SERIES_CONTEXT_NOT_FOUND")
        return {"data": context, "requestId": request.state.request_id}

    @router.patch("/projects/{project_id}/context")
    def patch_context(project_id: str, body: ContextPatchRequest, request: Request):
        project_or_404(project_id)
        current = repo.get(project_id)
        if current is None:
            raise HTTPException(404, "SERIES_CONTEXT_NOT_FOUND")
        context = deepcopy(current)
        # Explicit user edits win. Historical episode snapshots are never rewritten.
        for key, value in body.context.items():
            if key == "episodeSnapshots":
                raise HTTPException(400, "EPISODE_SNAPSHOTS_APPEND_ONLY")
            context[key] = deepcopy(value)
        repo.save(project_id, context)
        return {"data": context, "requestId": request.state.request_id}

    @router.post("/projects/{project_id}/episodes/{episode_id}/snapshot")
    def create_episode_snapshot(project_id: str, episode_id: str, request: Request):
        project_or_404(project_id)
        episode = runtime.repositories.episodes.get(episode_id)
        if episode is None or episode.project_id != project_id:
            raise HTTPException(404, "EPISODE_NOT_FOUND")
        context = repo.get(project_id)
        if context is None:
            raise HTTPException(404, "SERIES_CONTEXT_NOT_FOUND")
        number = int(context.get("nextEpisodeNumber", 1))
        episode_context = build_episode_context(context, number)
        episode_context["episodeId"] = episode_id
        # Capture exact library versions used by this episode so later edits do not alter history.
        episode_context["characterVersions"] = {
            cid: runtime.characters.get(cid).version
            for cid in episode_context.get("characters", [])
            if runtime.characters.get(cid) is not None
        }
        episode_context["locationVersions"] = {
            lid: runtime.locations.get(lid).version
            for lid in episode_context.get("locations", [])
            if runtime.locations.get(lid) is not None
        }
        snapshot = repo.snapshot(project_id, number, episode_context, episode_id)
        context["nextEpisodeNumber"] = number + 1
        context.setdefault("episodeSnapshots", []).append({"episodeNumber": number, "episodeId": episode_id, "context": snapshot})
        repo.save(project_id, context)
        return {"data": snapshot, "requestId": request.state.request_id}

    @router.get("/projects/{project_id}/snapshots")
    def snapshots(project_id: str, request: Request):
        project_or_404(project_id)
        return {"data": repo.list_snapshots(project_id), "requestId": request.state.request_id}

    return router
