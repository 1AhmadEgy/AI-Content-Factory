from __future__ import annotations

import os
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.jobs import build_router as build_job_router
from .api.projects import build_router as build_project_router
from .api.v1.assets import build_router as build_assets_router
from .api.v1.batches import build_router as build_batch_router
from .api.v1.best_take import build_router as build_best_take_router
from .api.v1.content import build_router as build_content_router
from .api.v1.context import build_router as build_context_router
from .api.v1.episode_translations import build_router as build_episode_translation_router
from .api.v1.episodes import build_router as build_episode_router
from .api.v1.factory import build_router as build_factory_router
from .api.v1.library import build_router as build_library_router
from .api.v1.models import build_router as build_models_router
from .api.v1.pipeline import router as pipeline_router
from .api.v1.publishing import build_router as build_publishing_router
from .api.v1.qc import build_router as build_qc_router
from .api.v1.render import build_router as build_render_router
from .api.v1.scheduling import build_router as build_scheduling_router
from .api.v1.series import build_router as build_series_router
from .api.v1.shots import build_router as build_shots_router
from .api.v1.system import build_router as build_system_router
from .api.v1.translations import build_router as build_translation_router
from .infrastructure.asset_repository import SQLiteAssetRepository
from .infrastructure.sqlite import SQLiteJobRepository, SQLiteProjectRepository, SQLiteRepositories
from .orchestrator.job_service import JobService
from .orchestrator.runtime import OrchestratorRuntime
from .orchestrator.worker_loop import WorkerLoop
from .services.project_context import ProjectContextStore
from .scheduling.loop import SchedulerLoop
from .scheduling.persistent import PersistentScheduler, SQLiteScheduleRepository

DATABASE_PATH = os.getenv("AICF_DATABASE_PATH", "./data/factory.db")
repositories = SQLiteRepositories(DATABASE_PATH)
job_repository = SQLiteJobRepository(repositories.store)
project_repository = SQLiteProjectRepository(repositories.store)
asset_repository = SQLiteAssetRepository(repositories.store)
orchestrator_runtime = OrchestratorRuntime(repositories)
context_store = orchestrator_runtime.context
worker_id = os.getenv("AICF_WORKER_ID", "auto")
worker_loop = WorkerLoop(orchestrator_runtime, worker_id=worker_id)


def _worker_autostart_enabled() -> bool:
    return os.getenv("AICF_WORKER_AUTOSTART", "false").strip().lower() in {"1", "true", "yes", "on"}


def _scheduler_autostart_enabled() -> bool:
    return os.getenv("AICF_SCHEDULER_AUTOSTART", "true").strip().lower() in {"1", "true", "yes", "on"}


def _api_token() -> str | None:
    token = os.getenv("AICF_API_TOKEN", "").strip()
    return token or None


schedule_repository = SQLiteScheduleRepository(repositories.store)
job_service = JobService(job_repository)


def _enqueue_scheduled(schedule):
    from .domain.jobs import JobInput, JobType
    payload = schedule.payload
    job_type = JobType(payload.get("type", schedule.operation).upper())
    job = job_service.create(project_id=schedule.project_id, job_type=job_type, target_type=payload.get("targetType", "scheduled"), target_id=payload.get("targetId"), parent_job_id=payload.get("parentJobId"), priority=int(payload.get("priority", 100)), max_attempts=int(payload.get("maxAttempts", 3)), provider=payload.get("provider"), model=payload.get("model"), input=JobInput(parameters=payload.get("parameters", payload), reference_asset_ids=payload.get("referenceAssetIds", []), constraints=payload.get("constraints", {}), seed=payload.get("seed"), deterministic=bool(payload.get("deterministic", False))))
    orchestrator_runtime.queue.enqueue(job)
    return job


persistent_scheduler = PersistentScheduler(schedule_repository, _enqueue_scheduled)
scheduler_loop = SchedulerLoop(persistent_scheduler, float(os.getenv("AICF_SCHEDULER_INTERVAL_SECONDS", "5")))


@asynccontextmanager
async def lifespan(_: FastAPI):
    if _worker_autostart_enabled():
        worker_loop.start()
    if _scheduler_autostart_enabled():
        scheduler_loop.start()
    try:
        yield
    finally:
        scheduler_loop.stop()
        worker_loop.stop()


app = FastAPI(title="AI Content Factory API", version="0.9.0", docs_url="/api/v1/docs", redoc_url="/api/v1/redoc", openapi_url="/api/v1/openapi.json", lifespan=lifespan)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or f"req_{uuid4().hex}"
    request.state.request_id = request_id
    if _api_token() and request.url.path not in {"/api/v1/health", "/api/v1/ready", "/api/v1/readiness"} and request.headers.get("Authorization", "") != f"Bearer {_api_token()}":
        return JSONResponse(status_code=401, content={"error": {"code": "UNAUTHORIZED", "message": "Authentication required", "details": {}, "requestId": request_id}}, headers={"X-Request-Id": request_id})
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception(request: Request, exc: StarletteHTTPException):
    request_id = getattr(request.state, "request_id", "unknown")
    code = str(exc.detail) if isinstance(exc.detail, str) else "HTTP_ERROR"
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": code, "details": {}, "requestId": request_id}, "detail": code}, headers={"X-Request-Id": request_id})


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error", "details": {}, "requestId": request_id}}, headers={"X-Request-Id": request_id})


app.include_router(build_project_router(project_repository))
app.include_router(build_job_router(job_repository, runtime=orchestrator_runtime, events=orchestrator_runtime.events))
app.include_router(build_batch_router(project_repository, job_repository, orchestrator_runtime))
app.include_router(build_scheduling_router(project_repository, schedule_repository, persistent_scheduler))
app.include_router(build_factory_router(project_repository, job_repository, orchestrator_runtime))
app.include_router(build_library_router())
app.include_router(build_series_router(orchestrator_runtime))
app.include_router(build_translation_router(repositories.store))
app.include_router(build_episode_translation_router(repositories.store))
app.include_router(build_content_router(orchestrator_runtime, job_repository))
app.include_router(build_assets_router(asset_repository))
app.include_router(build_models_router(orchestrator_runtime))
app.include_router(build_publishing_router(orchestrator_runtime, job_repository))
app.include_router(build_qc_router(orchestrator_runtime, job_repository))
app.include_router(build_best_take_router(orchestrator_runtime, job_repository))
app.include_router(build_render_router(orchestrator_runtime, job_repository))
app.include_router(build_system_router(orchestrator_runtime))
app.include_router(pipeline_router)
app.include_router(build_shots_router(orchestrator_runtime))
app.include_router(build_episode_router(orchestrator_runtime))
app.include_router(build_context_router(project_repository, context_store))


@app.get("/api/v1/health", tags=["system"])
def health(request: Request):
    return {"status": "ok", "data": {"status": "OK", "service": "ai-content-factory-backend", "version": app.version}, "requestId": request.state.request_id}


@app.get("/api/v1/ready", tags=["system"])
def readiness(request: Request):
    try:
        repositories.store.connection.execute("SELECT 1").fetchone()
        return {"status": "ready", "data": {"status": "READY", "service": "ai-content-factory-backend", "version": app.version}, "requestId": request.state.request_id}
    except Exception:
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(status_code=503, content={"error": {"code": "RESOURCE_UNAVAILABLE", "message": "Required dependencies are not ready", "details": {}, "requestId": request_id}}, headers={"X-Request-Id": request_id})


@app.get("/api/v1/worker/status", tags=["system"])
def worker_status(request: Request):
    return {"data": {"workerId": worker_loop.worker_id, "running": worker_loop.running, "autostart": _worker_autostart_enabled(), "iterations": worker_loop.iterations, "lastError": worker_loop.last_error}, "requestId": request.state.request_id}


@app.get("/api/v1/scheduler/status", tags=["scheduling"])
def scheduler_status(request: Request):
    return {"data": {"running": scheduler_loop.running, "autostart": _scheduler_autostart_enabled(), "ticks": scheduler_loop.ticks, "lastError": scheduler_loop.last_error}, "requestId": request.state.request_id}


@app.get("/api/v1/readiness", include_in_schema=False)
def readiness_alias(request: Request):
    return readiness(request)
