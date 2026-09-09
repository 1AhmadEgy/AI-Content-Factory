from fastapi import FastAPI

app = FastAPI(
    title="AI Content Factory API",
    version="0.1.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-content-factory-backend"}


@app.get("/api/v1/readiness", tags=["system"])
def readiness() -> dict[str, str]:
    # Persistence/queue checks will be added before this endpoint is used for production traffic.
    return {"status": "ready", "service": "ai-content-factory-backend"}
