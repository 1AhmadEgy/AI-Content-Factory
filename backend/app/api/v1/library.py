from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ...library.country_catalog import get_country_languages, get_country_library, list_country_libraries
from ...library.languages import get_language, list_languages


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/library", tags=["library"])

    @router.get("/countries")
    def countries(request: Request):
        return {"data": list_country_libraries(), "requestId": request.state.request_id}

    @router.get("/countries/{country_id}")
    def country(country_id: str, request: Request):
        value = get_country_library(country_id)
        if value is None:
            raise HTTPException(404, "COUNTRY_LIBRARY_NOT_FOUND")
        return {"data": value, "requestId": request.state.request_id}

    @router.get("/countries/{country_id}/languages")
    def country_languages(country_id: str, request: Request):
        if get_country_library(country_id) is None:
            raise HTTPException(404, "COUNTRY_LIBRARY_NOT_FOUND")
        return {"data": get_country_languages(country_id), "requestId": request.state.request_id}

    @router.get("/languages")
    def languages(request: Request):
        return {"data": list_languages(), "requestId": request.state.request_id}

    @router.get("/languages/{language_id}")
    def language(language_id: str, request: Request):
        value = get_language(language_id)
        if value is None:
            raise HTTPException(404, "LANGUAGE_NOT_FOUND")
        return {"data": value, "requestId": request.state.request_id}

    return router
