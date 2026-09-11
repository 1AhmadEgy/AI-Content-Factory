import os

os.environ["AICF_DATABASE_PATH"] = ":memory:"

from fastapi.testclient import TestClient

from backend.app.main import app


def test_factory_plan_requires_real_provider() -> None:
    response = TestClient(app).post("/api/v1/factory/plan", json={"topic": "A future city in 2050", "language": "ar", "durationSeconds": 60, "style": "documentary", "audience": "general", "platform": "youtube", "aspectRatio": "16:9"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_PROVIDER_NOT_CONFIGURED:story"


def test_factory_start_requires_real_provider() -> None:
    client = TestClient(app)
    project_id = client.post("/api/v1/projects", json={"name": "Factory Demo"}).json()["data"]["id"]
    response = client.post(f"/api/v1/factory/projects/{project_id}/start", json={"topic": "How AI works for beginners", "language": "ar", "durationSeconds": 60, "style": "educational", "audience": "general", "platform": "youtube", "aspectRatio": "16:9"}, headers={"Idempotency-Key": "factory-start-001"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_PROVIDER_NOT_CONFIGURED:story"


def test_factory_start_rejects_invalid_aspect_ratio() -> None:
    client = TestClient(app)
    project_id = client.post("/api/v1/projects", json={"name": "Validation"}).json()["data"]["id"]
    response = client.post(f"/api/v1/factory/projects/{project_id}/start", json={"topic": "test", "aspectRatio": "invalid"}, headers={"Idempotency-Key": "factory-validation-001"})
    assert response.status_code == 422
