from __future__ import annotations

from copy import deepcopy
from typing import Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...library.series_templates import get_series_template, list_series_templates
from ...library.continuity import build_episode_context, merge_series_defaults, new_series_context
from ...library.country_catalog import get_country_library, get_country_languages
from ...infrastructure.series_context_repository import SQLiteSeriesContextRepository


class ApplyTemplateRequest(BaseModel):
    templateId: str = Field(min_length=1, max_length=100)
    title: str | None = Field(default=None, max_length=500)
    countryId: str = Field(default="egypt", min_length=2, max_length=50)
    sourceLanguage: str | None = Field(default=None, min_length=2, max_length=20)
    targetLanguages: list[str] = Field(default_factory=list, max_length=20)
    dialect: str | None = Field(default=None, max_length=30)


class ContextPatchRequest(BaseModel):
    context: dict[str, Any]


def _language_defaults(country_id: str, source_language: str | None, target_languages: list[str], dialect: str | None) -> dict[str, Any]:
    country = get_country_library(country_id)
    if country is None:
        raise HTTPException(404, "COUNTRY_LIBRARY_NOT_FOUND")
    allowed = {item["id"] for item in get_country_languages(country_id)}
    source = source_language or str(country["defaultLanguage"])
    targets = list(dict.fromkeys(target_languages or [source]))
    if source not in allowed or any(item not in allowed for item in targets):
        raise HTTPException(400, "LANGUAGE_NOT_SUPPORTED_BY_COUNTRY")
    return {"countryId": country_id, "libraryId": country["libraryId"], "sourceLanguage": source, "targetLanguages": targets, "dialect": dialect or country["locale"], "translationPolicy": {"preserveSource": True, "manualOverridesWin": True, "immutableVersions": True}, "glossary": {}, "translationVersions": {}}


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
        language_defaults = _language_defaults(body.countryId, body.sourceLanguage, body.targetLanguages, body.dialect)
        defaults = template.get("defaults", {})
        current = repo.get(project_id)
        if current is None:
            context = new_series_context(series_id=project_id, title=body.title or template["name"], template_id=body.templateId, genre=template.get("genre", ""), character_ids=list(defaults.get("characterIds", [])), location_ids=list(defaults.get("locationIds", [])))
            context = merge_series_defaults(context, character_ids=list(defaults.get("characterIds", [])), location_ids=list(defaults.get("locationIds", [])), rules=dict(template.get("continuity", {})))
            context["template"] = deepcopy(template)
            context.update(language_defaults)
        else:
            context = current
            context["templateId"] = context.get("templateId") or body.templateId
            context["genre"] = context.get("genre") or template.get("genre", "")
            context = merge_series_defaults(context, character_ids=list(defaults.get("characterIds", [])), location_ids=list(defaults.get("locationIds", [])), rules=dict(template.get("continuity", {})))
            for key, value in language_defaults.items():
                if key not in context or context.get(key) in (None, "", [], {}):
                    context[key] = value
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
        if "countryId" in body.context:
            country_id = str(body.context["countryId"])
            if get_country_library(country_id) is None:
                raise HTTPException(404, "COUNTRY_LIBRARY_NOT_FOUND")
        for key, value in body.context.items():
            if key == "episodeSnapshots":
                raise HTTPException(400, "EPISODE_SNAPSHOTS_APPEND_ONLY")
            context[key] = deepcopy(value)
        repo.save(project_id, context)
        return {"data": context, "requestId": request.state.request_id}

    @router.post("/projects/{project_id}/episodes/{episode_id}/snapshot")
    def create_episode_snapshot(project_id: str, episode_id: str, request: Request):
        project_or_404(project_id)
        existing = repo.find_snapshot(project_id, episode_id)
        if existing is not None:
            return {"data": existing["context"], "requestId": request.state.request_id, "idempotent": True}
        context = repo.get(project_id)
        if context is None:
            raise HTTPException(404, "SERIES_CONTEXT_NOT_FOUND")
        number = int(context.get("nextEpisodeNumber", 1))
        episode_context = build_episode_context(context, number)
        episode_context["episodeId"] = episode_id
        episode_context["characterVersions"] = {cid: character.version for cid in episode_context.get("characters", []) if (character := runtime.characters.get(cid)) is not None}
        episode_context["locationVersions"] = {lid: location.version for lid in episode_context.get("locations", []) if (location := runtime.locations.get(lid)) is not None}
        snapshot = repo.snapshot(project_id, number, episode_context, episode_id)
        context["nextEpisodeNumber"] = number + 1
        context.setdefault("episodeSnapshots", []).append({"episodeNumber": number, "episodeId": episode_id, "context": snapshot})
        repo.save(project_id, context)
        return {"data": snapshot, "requestId": request.state.request_id, "idempotent": False}

    @router.get("/projects/{project_id}/snapshots")
    def snapshots(project_id: str, request: Request):
        project_or_404(project_id)
        return {"data": repo.list_snapshots(project_id), "requestId": request.state.request_id}

    return router
