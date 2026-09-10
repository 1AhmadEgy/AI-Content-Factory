from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ...orchestrator.runtime import OrchestratorRuntime


class SelectModelRequest(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    capability: str | None = Field(default=None, max_length=100)


def _serialize(model) -> dict:
    capability = model.adapter.capability()
    return {
        "id": model.id,
        "provider": model.provider,
        "enabled": model.enabled,
        "priority": model.priority,
        "healthy": model.adapter.health_check(),
        "capability": {
            "category": capability.category,
            "capabilities": sorted(capability.capabilities),
            "runtime": capability.runtime,
            "licenseStatus": capability.license_status,
        },
    }


def build_router(runtime: OrchestratorRuntime) -> APIRouter:
    router = APIRouter(prefix="/api/v1/models", tags=["models"])

    @router.get("")
    def list_models(request: Request) -> dict:
        return {"data": [_serialize(runtime.providers.get(mid)) for mid in runtime.providers.ids()], "requestId": request.state.request_id}

    @router.get("/{model_id}")
    def get_model(model_id: str, request: Request) -> dict:
        try:
            model = runtime.providers.get(model_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="MODEL_NOT_FOUND")
        return {"data": _serialize(model), "requestId": request.state.request_id}

    @router.post("/{model_id}/enable")
    def enable_model(model_id: str, request: Request) -> dict:
        try:
            runtime.providers.enable(model_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="MODEL_NOT_FOUND")
        return {"data": _serialize(runtime.providers.get(model_id)), "requestId": request.state.request_id}

    @router.post("/{model_id}/disable")
    def disable_model(model_id: str, request: Request) -> dict:
        try:
            runtime.providers.disable(model_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="MODEL_NOT_FOUND")
        return {"data": _serialize(runtime.providers.get(model_id)), "requestId": request.state.request_id}

    @router.post("/select")
    def select_model(body: SelectModelRequest, request: Request) -> dict:
        model = runtime.providers.route(body.category, body.capability)
        if model is None:
            raise HTTPException(status_code=503, detail="MODEL_UNAVAILABLE")
        return {"data": _serialize(model), "requestId": request.state.request_id}

    return router
