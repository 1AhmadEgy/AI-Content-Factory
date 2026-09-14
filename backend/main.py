from fastapi import Depends, FastAPI

from .auth import require_api_key

app = FastAPI(title="AI Content Factory API", version="1.0.0")


@app.get("/health")
def health() -> dict:
    return {"status": "OK", "version": app.version}


@app.get("/ready")
def ready() -> dict:
    return {"status": "READY", "version": app.version}


@app.get("/capabilities", dependencies=[Depends(require_api_key)])
def capabilities() -> dict:
    return {
        "status": "READY",
        "version": app.version,
        "capabilities": {
            "story": True,
            "image": True,
            "video": False,
            "tts": True,
            "render": True,
        },
    }


@app.get("/api/v1/auth/check", dependencies=[Depends(require_api_key)])
def auth_check() -> dict:
    return {"data": {"authenticated": True}}


@app.get("/api/v1/projects", dependencies=[Depends(require_api_key)])
def list_projects() -> dict:
    return {
        "data": [],
        "pagination": {"page": 1, "pageSize": 50, "total": 0, "hasNext": False},
    }
