from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...application.translation_service import TranslationProviderUnavailable, TranslationService
from ...domain.translation import TranslationRequest
from ...infrastructure.translation_repository import SQLiteTranslationRepository
from ...library.languages import list_languages


class TranslationBody(BaseModel):
    sourceLanguage: str = Field(min_length=2, max_length=20)
    targetLanguage: str = Field(min_length=2, max_length=20)
    text: str = Field(min_length=1)
    contentType: str = Field(default="dialogue", min_length=1, max_length=50)
    sourceId: str | None = None
    sourceVersion: int = Field(default=1, ge=1)
    preserveTerms: list[str] = Field(default_factory=list)
    glossary: dict[str, str] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    manualText: str | None = None
    provider: str | None = None
    model: str | None = None
    version: int = Field(default=1, ge=1)


class TranslationBatchBody(BaseModel):
    sourceLanguage: str = Field(min_length=2, max_length=20)
    targetLanguages: list[str] = Field(min_length=1, max_length=20)
    text: str = Field(min_length=1)
    contentType: str = Field(default="dialogue", min_length=1, max_length=50)
    sourceId: str | None = None
    sourceVersion: int = Field(default=1, ge=1)
    preserveTerms: list[str] = Field(default_factory=list)
    glossary: dict[str, str] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    provider: str | None = None
    model: str | None = None
    version: int = Field(default=1, ge=1)
    manualTexts: dict[str, str] = Field(default_factory=dict)


def _serialize(result):
    return {"id": result.id, "sourceLanguage": result.source_language, "targetLanguage": result.target_language, "sourceText": result.source_text, "translatedText": result.translated_text, "contentType": result.content_type, "sourceId": result.source_id, "provider": result.provider, "model": result.model, "glossaryVersion": result.glossary_version, "version": result.version, "manual": result.manual, "createdAt": result.created_at, "metadata": result.metadata}


def build_router(store=None) -> APIRouter:
    router = APIRouter(prefix="/api/v1/translations", tags=["translations"])
    repository = SQLiteTranslationRepository(store) if store is not None else None

    @router.get("/languages")
    def languages(request: Request):
        return {"data": list_languages(), "requestId": request.state.request_id}

    @router.get("")
    def history(request: Request, sourceId: str | None = None, targetLanguage: str | None = None, limit: int = 100):
        if repository is None:
            return {"data": [], "requestId": request.state.request_id}
        return {"data": [_serialize(item) for item in repository.list(source_id=sourceId, target_language=targetLanguage, limit=limit)], "requestId": request.state.request_id}

    @router.get("/{translation_id}")
    def get_translation(translation_id: str, request: Request):
        if repository is None:
            raise HTTPException(404, "TRANSLATION_NOT_FOUND")
        result = repository.get(translation_id)
        if result is None:
            raise HTTPException(404, "TRANSLATION_NOT_FOUND")
        return {"data": _serialize(result), "requestId": request.state.request_id}

    def _request(body: TranslationBody, target: str) -> TranslationRequest:
        return TranslationRequest(source_language=body.sourceLanguage, target_language=target, text=body.text, content_type=body.contentType, source_id=body.sourceId, source_version=body.sourceVersion, preserve_terms=tuple(body.preserveTerms), glossary=body.glossary, context=body.context)

    @router.post("")
    def translate(body: TranslationBody, request: Request):
        if body.sourceLanguage == body.targetLanguage and body.manualText is not None and body.manualText != body.text:
            raise HTTPException(400, "IDENTITY_TRANSLATION_MUST_MATCH_SOURCE")
        try:
            translation_request = _request(body, body.targetLanguage)
            if repository is not None and body.manualText is None:
                existing = repository.latest(translation_request)
                if existing is not None:
                    return {"data": _serialize(existing), "requestId": request.state.request_id, "idempotent": True}
            result = TranslationService().translate(translation_request, manual_text=body.manualText, provider=body.provider, model=body.model, version=body.version)
            if repository is not None:
                repository.save(result, translation_request)
        except TranslationProviderUnavailable:
            raise HTTPException(503, "TRANSLATION_PROVIDER_NOT_CONFIGURED")
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        return {"data": _serialize(result), "requestId": request.state.request_id}

    @router.post("/batch")
    def translate_batch(body: TranslationBatchBody, request: Request):
        targets = list(dict.fromkeys(body.targetLanguages))
        if len(targets) > 20:
            raise HTTPException(400, "TRANSLATION_BATCH_TOO_LARGE")
        results: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for target in targets:
            try:
                translation_request = TranslationRequest(source_language=body.sourceLanguage, target_language=target, text=body.text, content_type=body.contentType, source_id=body.sourceId, source_version=body.sourceVersion, preserve_terms=tuple(body.preserveTerms), glossary=body.glossary, context=body.context)
                manual_text = body.manualTexts.get(target)
                if repository is not None and manual_text is None:
                    existing = repository.latest(translation_request)
                    if existing is not None:
                        results.append(_serialize(existing))
                        continue
                result = TranslationService().translate(translation_request, manual_text=manual_text, provider=body.provider, model=body.model, version=body.version)
                if repository is not None:
                    repository.save(result, translation_request)
                results.append(_serialize(result))
            except TranslationProviderUnavailable:
                errors.append({"targetLanguage": target, "error": "TRANSLATION_PROVIDER_NOT_CONFIGURED"})
            except ValueError as exc:
                errors.append({"targetLanguage": target, "error": str(exc)})
        if errors and not results:
            raise HTTPException(503 if all(e["error"] == "TRANSLATION_PROVIDER_NOT_CONFIGURED" for e in errors) else 400, {"results": results, "errors": errors})
        return {"data": results, "errors": errors, "requestId": request.state.request_id}

    return router
