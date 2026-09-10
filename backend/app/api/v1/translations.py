from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...application.translation_service import TranslationProviderUnavailable, TranslationService
from ...library.languages import list_languages


class TranslationBody(BaseModel):
    sourceLanguage: str = Field(min_length=2, max_length=20)
    targetLanguage: str = Field(min_length=2, max_length=20)
    text: str = Field(min_length=1)
    contentType: str = Field(default="text", min_length=1, max_length=50)
    sourceId: str | None = None
    preserveTerms: list[str] = Field(default_factory=list)
    glossary: dict[str, str] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    manualText: str | None = None
    provider: str | None = None
    model: str | None = None
    version: int = Field(default=1, ge=1)


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/translations", tags=["translations"])
    service = TranslationService()

    @router.get("/languages")
    def languages(request: Request):
        return {"data": list_languages(), "requestId": request.state.request_id}

    @router.post("")
    def translate(body: TranslationBody, request: Request):
        if body.sourceLanguage == body.targetLanguage and body.manualText is not None and body.manualText != body.text:
            raise HTTPException(400, "IDENTITY_TRANSLATION_MUST_MATCH_SOURCE")
        try:
            result = service.translate(
                __import__("backend.app.domain.translation", fromlist=["TranslationRequest"]).TranslationRequest(
                    source_language=body.sourceLanguage,
                    target_language=body.targetLanguage,
                    text=body.text,
                    content_type=body.contentType,
                    source_id=body.sourceId,
                    preserve_terms=tuple(body.preserveTerms),
                    glossary=body.glossary,
                    context=body.context,
                ),
                manual_text=body.manualText,
                provider=body.provider,
                model=body.model,
                version=body.version,
            )
        except TranslationProviderUnavailable:
            raise HTTPException(503, "TRANSLATION_PROVIDER_NOT_CONFIGURED")
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        return {"data": {
            "id": result.id,
            "sourceLanguage": result.source_language,
            "targetLanguage": result.target_language,
            "sourceText": result.source_text,
            "translatedText": result.translated_text,
            "contentType": result.content_type,
            "sourceId": result.source_id,
            "provider": result.provider,
            "model": result.model,
            "version": result.version,
            "manual": result.manual,
            "createdAt": result.created_at,
        }, "requestId": request.state.request_id}

    return router
