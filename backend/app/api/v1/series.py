from __future__ import annotations

from copy import deepcopy
from typing import Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...application.translation_pipeline import ContentSegment, TranslationPipeline
from ...library.series_templates import get_series_template, list_series_templates
from ...library.continuity import build_episode_context, merge_series_defaults, new_series_context
from ...library.country_catalog import get_country_library, get_country_languages
from ...infrastructure.series_context_repository import SQLiteSeriesContextRepository
from ...infrastructure.translation_repository import SQLiteTranslationRepository


class ApplyTemplateRequest(BaseModel):
    templateId: str = Field(min_length=1, max_length=100)
    title: str | None = Field(default=None, max_length=500)
    countryId: str | None = Field(default=None, min_length=2, max_length=50)
    sourceLanguage: str | None = Field(default=None, min_length=2, max_length=20)
    targetLanguages: list[str] = Field(default_factory=list, max_length=20)
    dialect: str | None = Field(default=None, max_length=30)


class ContextPatchRequest(BaseModel):
    context: dict[str, Any]


class SeriesTranslationSegment(BaseModel):
    id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)
    contentType: str = Field(default="dialogue", min_length=1, max_length=50)
    version: int = Field(default=1, ge=1)
    context: dict[str, Any] = Field(default_factory=dict)
    preserveTerms: list[str] = Field(default_factory=list)


class SeriesTranslationRequest(BaseModel):
    segments: list[SeriesTranslationSegment] = Field(min_length=1, max_length=500)
    targetLanguages: list[str] | None = Field(default=None, max_length=20)
    glossary: dict[str, str] | None = None
    provider: str | None = None
    model: str | None = None
    translationVersion: int = Field(default=1, ge=1)
    manualTexts: dict[str, dict[str, str]] = Field(default_factory=dict)


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


def _project_country(project: Any) -> str | None:
    settings = getattr(project, "settings", None)
    if isinstance(settings, dict):
        for key in ("countryId", "country_id"):
            value = settings.get(key)
            if value:
                return str(value)
    metadata = getattr(project, "metadata", None)
    if isinstance(metadata, dict):
        for key in ("countryId", "country_id"):
            value = metadata.get(key)
            if value:
                return str(value)
    return None


def _resolve_country_id(project: Any, current: dict[str, Any] | None, requested: str | None) -> str:
    existing = str(current.get("countryId")) if current and current.get("countryId") else None
    project_country = _project_country(project)
    if existing and requested and existing != requested:
        raise HTTPException(409, "COUNTRY_LIBRARY_MISMATCH")
    if existing:
        return existing
    if requested:
        return requested
    if project_country:
        return project_country
    return "egypt"


def _country_owned_defaults(runtime: Any, defaults: dict[str, Any], library_id: str) -> tuple[list[str], list[str]]:
    character_ids: list[str] = []
    for value in defaults.get("characterIds", []):
        item = runtime.characters.get(str(value))
        if item is not None and str(item.project_id) == library_id:
            character_ids.append(str(value))
    location_ids: list[str] = []
    for value in defaults.get("locationIds", []):
        item = runtime.locations.get(str(value))
        if item is not None and str(item.project_id) == library_id:
            location_ids.append(str(value))
    return character_ids, location_ids


def _validate_context_language(context: dict[str, Any]) -> None:
    country_id = str(context.get("countryId", ""))
    country = get_country_library(country_id)
    if country is None:
        raise HTTPException(404, "COUNTRY_LIBRARY_NOT_FOUND")
    expected_library = str(country["libraryId"])
    if context.get("libraryId") and str(context["libraryId"]) != expected_library:
        raise HTTPException(409, "COUNTRY_LIBRARY_MISMATCH")
    allowed = {item["id"] for item in get_country_languages(country_id)}
    source = context.get("sourceLanguage")
    targets = context.get("targetLanguages", [])
    if source and str(source) not in allowed:
        raise HTTPException(400, "LANGUAGE_NOT_SUPPORTED_BY_COUNTRY")
    if any(str(item) not in allowed for item in targets):
        raise HTTPException(400, "LANGUAGE_NOT_SUPPORTED_BY_COUNTRY")


def build_router(runtime) -> APIRouter:
    router = APIRouter(prefix="/api/v1/series", tags=["series"])
    repo = SQLiteSeriesContextRepository(runtime.repositories.store)
    translation_repo = SQLiteTranslationRepository(runtime.repositories.store)

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
        project = project_or_404(project_id)
        template = get_series_template(body.templateId)
        if template is None:
            raise HTTPException(404, "SERIES_TEMPLATE_NOT_FOUND")
        current = repo.get(project_id)
        country_id = _resolve_country_id(project, current, body.countryId)
        language_defaults = _language_defaults(country_id, body.sourceLanguage, body.targetLanguages, body.dialect)
        defaults = template.get("defaults", {})
        character_ids, location_ids = _country_owned_defaults(runtime, defaults, language_defaults["libraryId"])
        if current is None:
            context = new_series_context(series_id=project_id, title=body.title or template["name"], template_id=body.templateId, genre=template.get("genre", ""), character_ids=character_ids, location_ids=location_ids)
            context = merge_series_defaults(context, character_ids=character_ids, location_ids=location_ids, rules=dict(template.get("continuity", {})))
            context["template"] = deepcopy(template)
            context["template"]["appliedCountryId"] = country_id
            context.update(language_defaults)
        else:
            context = current
            context["templateId"] = context.get("templateId") or body.templateId
            context["genre"] = context.get("genre") or template.get("genre", "")
            context = merge_series_defaults(context, character_ids=character_ids, location_ids=location_ids, rules=dict(template.get("continuity", {})))
            for key, value in language_defaults.items():
                if key not in context or context.get(key) in (None, "", [], {}):
                    context[key] = value
            _validate_context_language(context)
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
            existing_country = str(current.get("countryId", ""))
            if existing_country and existing_country != country_id:
                raise HTTPException(409, "COUNTRY_LIBRARY_MISMATCH")
            expected_library = str(get_country_library(country_id)["libraryId"])
            if "libraryId" in body.context and str(body.context["libraryId"]) != expected_library:
                raise HTTPException(409, "COUNTRY_LIBRARY_MISMATCH")
        for key, value in body.context.items():
            if key == "episodeSnapshots":
                raise HTTPException(400, "EPISODE_SNAPSHOTS_APPEND_ONLY")
            context[key] = deepcopy(value)
        _validate_context_language(context)
        repo.save(project_id, context)
        return {"data": context, "requestId": request.state.request_id}

    @router.post("/projects/{project_id}/translate")
    def translate_series(project_id: str, body: SeriesTranslationRequest, request: Request):
        """Translate series content using its immutable source/language contract."""
        project_or_404(project_id)
        context = repo.get(project_id)
        if context is None:
            raise HTTPException(404, "SERIES_CONTEXT_NOT_FOUND")
        _validate_context_language(context)

        source_language = str(context.get("sourceLanguage", ""))
        configured_targets = list(dict.fromkeys(str(item) for item in context.get("targetLanguages", [])))
        targets = list(dict.fromkeys(body.targetLanguages or configured_targets))
        allowed = {item["id"] for item in get_country_languages(str(context["countryId"]))}
        if source_language not in allowed or any(target not in allowed for target in targets):
            raise HTTPException(400, "LANGUAGE_NOT_SUPPORTED_BY_COUNTRY")
        if any(target not in configured_targets for target in targets):
            raise HTTPException(400, "TARGET_LANGUAGE_NOT_ENABLED_FOR_SERIES")
        if (context.get("translationPolicy") or {}).get("preserveSource") is False:
            raise HTTPException(409, "SERIES_TRANSLATION_SOURCE_MUST_BE_PRESERVED")

        glossary = dict(context.get("glossary") or {})
        if body.glossary is not None:
            glossary.update(body.glossary)
        segments = [
            ContentSegment(
                id=item.id,
                text=item.text,
                content_type=item.contentType,
                version=item.version,
                context={**item.context, "seriesId": project_id, "countryId": context.get("countryId"), "dialect": context.get("dialect")},
                preserve_terms=tuple(item.preserveTerms),
            )
            for item in body.segments
        ]
        output = TranslationPipeline(repository=translation_repo).translate_segments(
            segments,
            source_language=source_language,
            target_languages=targets,
            glossary=glossary,
            provider=body.provider,
            model=body.model,
            manual_texts=body.manualTexts,
            translation_version=body.translationVersion,
        )

        versions = dict(context.get("translationVersions") or {})
        versions[str(body.translationVersion)] = {
            "sourceLanguage": source_language,
            "targetLanguages": targets,
            "segmentCount": len(segments),
        }
        context["translationVersions"] = versions
        repo.save(project_id, context)
        return {
            "data": output["results"],
            "errors": output["errors"],
            "seriesId": project_id,
            "countryId": context.get("countryId"),
            "libraryId": context.get("libraryId"),
            "sourceLanguage": source_language,
            "targetLanguages": targets,
            "dialect": context.get("dialect"),
            "translationVersion": body.translationVersion,
            "sourcePreserved": True,
            "requestId": request.state.request_id,
        }

    @router.post("/projects/{project_id}/episodes/{episode_id}/snapshot")
    def create_episode_snapshot(project_id: str, episode_id: str, request: Request):
        project_or_404(project_id)
        existing = repo.find_snapshot(project_id, episode_id)
        if existing is not None:
            return {"data": existing["context"], "requestId": request.state.request_id, "idempotent": True}
        context = repo.get(project_id)
        if context is None:
            raise HTTPException(404, "SERIES_CONTEXT_NOT_FOUND")
        _validate_context_language(context)
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
