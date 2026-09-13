from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ...orchestrator.runtime import OrchestratorRuntime


def build_router(runtime: OrchestratorRuntime) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["system"])

    @router.get("/health")
    def health(request: Request) -> dict:
        return {"status": "ok", "data": {"status": "OK", "service": "ai-content-factory-backend", "version": "0.9.0"}, "requestId": request.state.request_id}

    @router.get("/ready", response_model=None)
    def readiness(request: Request) -> dict | JSONResponse:
        try:
            runtime.repositories.store.connection.execute("SELECT 1").fetchone()
            return {"status": "ready", "data": {"status": "READY", "service": "ai-content-factory-backend", "version": "0.9.0"}, "requestId": request.state.request_id}
        except Exception:
            request_id = getattr(request.state, "request_id", "unknown")
            return JSONResponse(status_code=503, content={"error": {"code": "RESOURCE_UNAVAILABLE", "message": "Required dependencies are not ready", "details": {}, "requestId": request_id}}, headers={"X-Request-Id": request_id})

    @router.get("/readiness", include_in_schema=False, response_model=None)
    def readiness_alias(request: Request) -> dict | JSONResponse:
        return readiness(request)

    @router.get("/capabilities")
    def capabilities(request: Request) -> dict:
        workers = runtime.workers.names()
        healthy = {name: runtime.workers.get(name).health_check() for name in workers}
        model_ids = runtime.providers.ids()
        return {
            "data": {
                "story": "provider-generation" in workers,
                "image": "provider-generation" in workers,
                "video": "provider-generation" in workers and "render" in workers,
                "tts": "provider-generation" in workers,
                "render": healthy.get("render", False),
                "qc": healthy.get("quality-control", False),
                "bestTake": healthy.get("best-take", False),
                "timeline": healthy.get("timeline", False),
                "subtitles": healthy.get("media-document", False),
                "thumbnail": healthy.get("media-document", False),
                "metadata": healthy.get("media-document", False),
                "publishing": healthy.get("publish", False),
                "repurpose": healthy.get("repurpose", False),
                "models": model_ids,
                "workers": healthy,
            },
            "requestId": request.state.request_id,
        }

    @router.get("/worker/registry")
    def worker_registry(request: Request) -> dict:
        return {
            "data": {
                "workers": [
                    {"id": name, "healthy": runtime.workers.get(name).health_check()}
                    for name in runtime.workers.names()
                ]
            },
            "requestId": request.state.request_id,
        }

    return router
