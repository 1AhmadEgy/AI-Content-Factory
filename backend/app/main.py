from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .api.jobs import build_router as build_job_router
from .api.projects import build_router as build_project_router
from .api.v1.factory import build_router as build_factory_router
from .api.v1.pipeline import router as pipeline_router
from .infrastructure.sqlite import SQLiteJobRepository, SQLiteProjectRepository, SQLiteRepositories
from .orchestrator.runtime import OrchestratorRuntime
from .orchestrator.worker_loop import WorkerLoop


DATABASE_PATH = os.getenv("AICF_DATABASE_PATH", "./data/factory.db")
if DATABASE_PATH != ":memory:":
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
repositories = SQLiteRepositories(DATABASE_PATH)
job_repository = SQLiteJobRepository(repositories.store)
project_repository = SQLiteProjectRepository(repositories.store)
orchestrator_runtime = OrchestratorRuntime(repositories)
worker_id = os.getenv("AICF_WORKER_ID", "mock")
worker_loop = WorkerLoop(orchestrator_runtime, worker_id=worker_id)


def _worker_autostart_enabled() -> bool:
    return os.getenv("AICF_WORKER_AUTOSTART", "false").strip().lower() in {"1", "true", "yes", "on"}


def _error_response(request: Request, status_code: int, code: str, message: str, details: object | None = None) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message, "details": details if details is not None else {}, "requestId": request_id}}, headers={"X-Request-Id": request_id})


@asynccontextmanager
async def lifespan(_: FastAPI):
    if _worker_autostart_enabled():
        worker_loop.start()
    try:
        yield
    finally:
        worker_loop.stop()


app = FastAPI(title="AI Content Factory API", version="0.3.0", docs_url="/api/v1/docs", redoc_url="/api/v1/redoc", openapi_url="/api/v1/openapi.json", lifespan=lifespan)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or f"req_{uuid4().hex}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    mapping = {400: "VALIDATION_ERROR", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "CONFLICT", 422: "DOMAIN_RULE_VIOLATION", 429: "RATE_LIMITED", 500: "INTERNAL_ERROR", 502: "PROVIDER_ERROR", 503: "RESOURCE_UNAVAILABLE", 504: "TIMEOUT"}
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    code = detail if isinstance(detail, str) and detail.isupper() and len(detail) <= 80 else mapping.get(exc.status_code, "INTERNAL_ERROR")
    message = detail if code == mapping.get(exc.status_code) else "Request failed"
    return _error_response(request, exc.status_code, code, message)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return _error_response(request, 400, "VALIDATION_ERROR", "Request validation failed", {"errors": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    return _error_response(request, 500, "INTERNAL_ERROR", "Internal server error")


app.include_router(build_project_router(project_repository))
app.include_router(build_job_router(job_repository, runtime=orchestrator_runtime, events=orchestrator_runtime.events))
app.include_router(build_factory_router(project_repository, job_repository, orchestrator_runtime))
app.include_router(pipeline_router)


@app.get("/api/v1/health", tags=["system"])
def health(request: Request) -> dict[str, object]:
    return {"data": {"status": "OK", "service": "ai-content-factory-backend"}, "requestId": request.state.request_id}


@app.get("/api/v1/ready", tags=["system"])
def readiness(request: Request) -> dict[str, object]:
    try:
        repositories.store.connection.execute("SELECT 1").fetchone()
        return {"data": {"status": "READY", "service": "ai-content-factory-backend"}, "requestId": request.state.request_id}
    except Exception:
        return _error_response(request, 503, "RESOURCE_UNAVAILABLE", "Required dependencies are not ready")


@app.get("/api/v1/worker/status", tags=["system"])
def worker_status(request: Request) -> dict[str, object]:
    return {"data": {"workerId": worker_loop.worker_id, "running": worker_loop.running, "autostart": _worker_autostart_enabled(), "iterations": worker_loop.iterations, "lastError": worker_loop.last_error}, "requestId": request.state.request_id}


@app.get("/api/v1/readiness", include_in_schema=False)
def readiness_alias(request: Request):
    return readiness(request)
