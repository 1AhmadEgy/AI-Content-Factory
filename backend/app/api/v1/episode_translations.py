from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...application.episode_translation_service import EpisodeTranslationService
from ...infrastructure.translation_repository import SQLiteTranslationRepository
from ...library.country_catalog import get_country_library, get_country_languages


class EpisodeLanguagePackBody(BaseModel):
    snapshot: dict[str, Any]
    targetLanguages: list[str] = Field(min_length=1, max_length=20)
    manualTexts: dict[str, str] = Field(default_factory=dict)
    version: int = Field(default=1, ge=1)


def build_router(store=None) -> APIRouter:
    router = APIRouter(prefix="/api/v1/episodes", tags=["episode-language-packs"])
    repository = SQLiteTranslationRepository(store) if store is not None else None

    @router.post("/{episode_id}/language-pack")
    def create_language_pack(episode_id: str, body: EpisodeLanguagePackBody, request: Request):
        snapshot = dict(body.snapshot)
        snapshot["episodeId"] = episode_id
        country_id = str(snapshot.get("countryId") or "")
        if not country_id:
            raise HTTPException(400, "EPISODE_COUNTRY_REQUIRED")
        country = get_country_library(country_id)
        if country is None:
            raise HTTPException(404, "COUNTRY_LIBRARY_NOT_FOUND")
        expected_library = str(country["libraryId"])
        if snapshot.get("libraryId") and str(snapshot["libraryId"]) != expected_library:
            raise HTTPException(409, "COUNTRY_LIBRARY_MISMATCH")
        allowed = {item["id"] for item in get_country_languages(country_id)}
        source_language = str(snapshot.get("sourceLanguage") or snapshot.get("language") or "")
        if source_language not in allowed:
            raise HTTPException(400, "LANGUAGE_NOT_SUPPORTED_BY_COUNTRY")
        targets = list(dict.fromkeys(body.targetLanguages))
        if any(target not in allowed for target in targets):
            raise HTTPException(400, "LANGUAGE_NOT_SUPPORTED_BY_COUNTRY")
        service = EpisodeTranslationService(repository=repository)
        try:
            result = service.translate_episode(snapshot, targets, manual_texts=body.manualTexts, version=body.version)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        return {"data": result, "requestId": request.state.request_id}

    return router
