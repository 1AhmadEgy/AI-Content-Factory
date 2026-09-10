from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ...infrastructure.sqlite import SQLiteRepositories


def build_router(repositories: SQLiteRepositories, version: str) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["system"])

    @router.get("/health")
    def health(request: Request) -> dict[str, object]:
        return {
            "status": "ok",
            "data": {
                "status": "OK",
                "service": "ai-content-factory-backend",
                "version": version,
            },
            "requestId": request.state.request_id,
        }

    @router.get("/ready", response_model=None)
    @router.get("/readiness", response_model=None)
    def readiness(request: Request) -> dict[str, object] | JSONResponse:
        try:
            repositories.store.connection.execute("SELECT 1").fetchone()
        except Exception:
            request_id = getattr(request.state, "request_id", "unknown")
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "code": "RESOURCE_UNAVAILABLE",
                        "message": "Required dependencies are not ready",
                        "details": {},
                        "requestId": request_id,
                    },
                    "detail": "RESOURCE_UNAVAILABLE",
                },
                headers={"X-Request-Id": request_id},
            )
        return {
            "status": "ready",
            "data": {
                "status": "READY",
                "service": "ai-content-factory-backend",
                "version": version,
            },
            "requestId": request.state.request_id,
        }

    return router
