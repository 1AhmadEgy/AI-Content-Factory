from __future__ import annotations

import os

from fastapi import FastAPI

from .api.jobs import build_router as build_job_router
from .api.projects import build_router as build_project_router
from .infrastructure.sqlite import SQLiteJobRepository, SQLiteProjectRepository, SQLiteRepositories


DATABASE_PATH = os.getenv("AICF_DATABASE_PATH", "./data/factory.db")
repositories = SQLiteRepositories(DATABASE_PATH)
job_repository = SQLiteJobRepository(repositories.store)
project_repository = SQLiteProjectRepository(repositories.store)

app = FastAPI(
    title="AI Content Factory API",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)
app.include_router(build_project_router(project_repository))
app.include_router(build_job_router(job_repository))


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-content-factory-backend"}


@app.get("/api/v1/readiness", tags=["system"])
def readiness() -> dict[str, str]:
    try:
        repositories.store.connection.execute("SELECT 1").fetchone()
        return {"status": "ready", "service": "ai-content-factory-backend"}
    except Exception:
        return {"status": "not_ready", "service": "ai-content-factory-backend"}
