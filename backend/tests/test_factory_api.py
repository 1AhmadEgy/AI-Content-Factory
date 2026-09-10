import os
os.environ["AICF_DATABASE_PATH"] = ":memory:"
from fastapi.testclient import TestClient
from backend.app.main import app

def test_factory_plan_returns_structured_story_scene_shot_data() -> None:
    client = TestClient(app)
    response = client.post("/api/v1/factory/plan", json={"topic": "A future city in 2050", "language": "ar", "durationSeconds": 60, "style": "documentary", "audience": "general", "platform": "youtube", "aspectRatio": "16:9"})
    assert response.status_code == 200
    plan = response.json()["data"]["plan"]
    assert plan["title"] == "A future city in 2050" and plan["scenes"] and plan["scenes"][0]["shots"]
    assert response.json()["requestId"]

def test_factory_start_creates_queued_story_job_and_is_idempotent() -> None:
    client = TestClient(app); project_id = client.post("/api/v1/projects", json={"name": "Factory Demo"}).json()["data"]["id"]
    payload = {"topic": "How AI works for beginners", "language": "ar", "durationSeconds": 60, "style": "educational", "audience": "general", "platform": "youtube", "aspectRatio": "16:9"}; headers = {"Idempotency-Key": "factory-start-001"}
    first = client.post(f"/api/v1/factory/projects/{project_id}/start", json=payload, headers=headers); second = client.post(f"/api/v1/factory/projects/{project_id}/start", json=payload, headers=headers)
    assert first.status_code == 202 and first.json()["data"]["stage"] == "STORY" and first.json()["data"]["status"] == "QUEUED"
    assert second.status_code == 202 and second.json()["data"]["jobId"] == first.json()["data"]["jobId"] and second.json()["idempotentReplay"] is True

def test_factory_start_rejects_invalid_aspect_ratio() -> None:
    client = TestClient(app); project_id = client.post("/api/v1/projects", json={"name": "Validation"}).json()["data"]["id"]
    response = client.post(f"/api/v1/factory/projects/{project_id}/start", json={"topic": "test", "aspectRatio": "invalid"}, headers={"Idempotency-Key": "factory-validation-001"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
