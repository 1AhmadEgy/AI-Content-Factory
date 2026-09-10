from __future__ import annotations

import os
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api.jobs import build_router as build_job_router
from .api.projects import build_router as build_project_router
from .api.v1.assets import build_router as build_assets_router
from .api.v1.best_take import build_router as build_best_take_router
from .api.v1.content import build_router as build_content_router
from .api.v1.factory import build_router as build_factory_router
from .api.v1.models import build_router as build_models_router
from .api.v1.pipeline import router as pipeline_router
from .api.v1.publishing import build_router as build_publishing_router
from .api.v1.qc import build_router as build_qc_router
from .api.v1.render import build_router as build_render_router
from .api.v1.system import build_router as build_system_router
from .infrastructure.asset_repository import SQLiteAssetRepository
from .infrastructure.sqlite import SQLiteJobRepository, SQLiteProjectRepository, SQLiteRepositories
from .orchestrator.runtime import OrchestratorRuntime
from .orchestrator.worker_loop import WorkerLoop

DATABASE_PATH = os.getenv("AICF_DATABASE_PATH", "./data/factory.db")
repositories = SQLiteRepositories(DATABASE_PATH)
job_repository = SQLiteJobRepository(repositories.store)
project_repository = SQLiteProjectRepository(repositories.store)
asset_repository = SQLiteAssetRepository(repositories.store)
orchestrator_runtime = OrchestratorRuntime(repositories)
worker_id = os.getenv("AICF_WORKER_ID", "auto")
worker_loop = WorkerLoop(orchestrator_runtime, worker_id=worker_id)


def _worker_autostart_enabled() -> bool:
    return os.getenv("AICF_WORKER_AUTOSTART", "false").strip().lower() in {"1", "true", "yes", "on"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    if _worker_autostart_enabled(): worker_loop.start()
    try: yield
    finally: worker_loop.stop()


app = FastAPI(title="AI Content Factory API", version="0.6.0", docs_url="/api/v1/docs", redoc_url="/api/v1/redoc", openapi_url="/api/v1/openapi.json", lifespan=lifespan)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or f"req_{uuid4().hex}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error", "details": {}, "requestId": request_id}}, headers={"X-Request-Id": request_id})


app.include_router(build_project_router(project_repository))
app.include_router(build_job_router(job_repository, runtime=orchestrator_runtime, events=orchestrator_runtime.events))
app.include_router(build_factory_router(project_repository, job_repository, orchestrator_runtime))
app.include_router(build_content_router(orchestrator_runtime, job_repository))
app.include_router(build_assets_router(asset_repository))
app.include_router(build_models_router(orchestrator_runtime))
app.include_router(build_publishing_router(orchestrator_runtime, job_repository))
app.include_router(build_qc_router(orchestrator_runtime, job_repository))
app.include_router(build_best_take_router(orchestrator_runtime, job_repository))
app.include_router(build_render_router(orchestrator_runtime, job_repository))
app.include_router(build_system_router(orchestrator_runtime))
app.include_router(pipeline_router)


@app.get("/api/v1/health", tags=["system"])
def health(request: Request) -> dict[str, object]:
    return {"status": "ok", "data": {"status": "OK", "service": "ai-content-factory-backend"}, "requestId": request.state.request_id}


@app.get("/api/v1/ready", tags=["system"])
def readiness(request: Request) -> dict[str, object]:
    try:
        repositories.store.connection.execute("SELECT 1").fetchone()
        return {"status": "ready", "data": {"status": "READY", "service": "ai-content-factory-backend"}, "requestId": request.state.request_id}
    except Exception:
        return JSONResponse(status_code=503, content={"error": {"code": "RESOURCE_UNAVAILABLE", "message": "Required dependencies are not ready", "details": {}, "requestId": request.state.request_id}}, headers={"X-Request-Id": request.state.request_id})


@app.get("/api/v1/worker/status", tags=["system"])
def worker_status(request: Request) -> dict[str, object]:
    return {"data": {"workerId": worker_loop.worker_id, "running": worker_loop.running, "autostart": _worker_autostart_enabled(), "iterations": worker_loop.iterations, "lastError": worker_loop.last_error}, "requestId": request.state.request_id}


@app.get("/api/v1/readiness", include_in_schema=False)
def readiness_alias(request: Request):
    return readiness(request)
