import os

os.environ["AICF_DATABASE_PATH"] = ":memory:"
os.environ.pop("OPENAI_API_KEY", None)

from fastapi.testclient import TestClient

from app.main import app


def test_factory_plan_fails_closed_without_real_provider() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/factory/plan",
        json={
            "topic": "A future city in 2050",
            "language": "ar",
            "durationSeconds": 60,
            "style": "documentary",
            "audience": "general",
            "platform": "youtube",
            "aspectRatio": "16:9",
        },
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_PROVIDER_UNAVAILABLE"
    assert "data" not in response.json()


def test_factory_start_fails_closed_without_real_provider() -> None:
    client = TestClient(app)
    project = client.post("/api/v1/projects", json={"name": "Factory Provider Check"})
    assert project.status_code == 201
    project_id = project.json()["data"]["id"]
    response = client.post(
        f"/api/v1/factory/projects/{project_id}/start",
        json={
            "topic": "How AI works for beginners",
            "language": "ar",
            "durationSeconds": 60,
            "style": "educational",
            "audience": "general",
            "platform": "youtube",
            "aspectRatio": "16:9",
        },
        headers={"Idempotency-Key": "factory-provider-check-001"},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AI_PROVIDER_UNAVAILABLE"


def test_factory_start_rejects_invalid_aspect_ratio_before_provider_call() -> None:
    client = TestClient(app)
    project = client.post("/api/v1/projects", json={"name": "Validation"})
    assert project.status_code == 201
    project_id = project.json()["data"]["id"]
    response = client.post(
        f"/api/v1/factory/projects/{project_id}/start",
        json={"topic": "test", "aspectRatio": "invalid"},
        headers={"Idempotency-Key": "factory-validation-001"},
    )
    assert response.status_code == 422
