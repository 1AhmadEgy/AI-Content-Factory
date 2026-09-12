import os

os.environ["AICF_DATABASE_PATH"] = ":memory:"

from fastapi.testclient import TestClient

from app.main import app


def test_create_project_then_job() -> None:
    client = TestClient(app)
    project_response = client.post("/api/v1/projects", json={"name": "Demo"})
    assert project_response.status_code == 201
    project_id = project_response.json()["data"]["id"]

    job_payload = {
        "projectId": project_id,
        "type": "IMAGE",
        "targetType": "shot",
        "input": {"parameters": {"prompt": "hello"}, "deterministic": True},
    }
    job_response = client.post("/api/v1/jobs", json=job_payload, headers={"Idempotency-Key": "test-job-001"})
    assert job_response.status_code == 202
    job_id = job_response.json()["data"]["id"]
    assert job_response.json()["data"]["status"] == "QUEUED"
    assert job_response.headers["X-Request-Id"]

    get_response = client.get(f"/api/v1/jobs/{job_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == job_id


def test_job_idempotency_replays_same_job() -> None:
    client = TestClient(app)
    project_id = client.post("/api/v1/projects", json={"name": "Idempotency"}).json()["data"]["id"]
    payload = {"projectId": project_id, "type": "IMAGE", "targetType": "shot"}
    headers = {"Idempotency-Key": "replay-001"}

    first = client.post("/api/v1/jobs", json=payload, headers=headers)
    second = client.post("/api/v1/jobs", json=payload, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    assert second.json()["idempotentReplay"] is True


def test_job_idempotency_conflict_on_changed_body() -> None:
    client = TestClient(app)
    project_id = client.post("/api/v1/projects", json={"name": "Conflict"}).json()["data"]["id"]
    headers = {"Idempotency-Key": "conflict-001"}

    first = client.post("/api/v1/jobs", json={"projectId": project_id, "type": "IMAGE", "targetType": "shot"}, headers=headers)
    second = client.post("/api/v1/jobs", json={"projectId": project_id, "type": "VIDEO", "targetType": "shot"}, headers=headers)

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["detail"] == "IDEMPOTENCY_CONFLICT"


def test_missing_idempotency_key_is_rejected() -> None:
    client = TestClient(app)
    project_id = client.post("/api/v1/projects", json={"name": "NoKey"}).json()["data"]["id"]
    response = client.post("/api/v1/jobs", json={"projectId": project_id, "type": "IMAGE", "targetType": "shot"})
    assert response.status_code == 400
    assert response.json()["detail"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_get_missing_job() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/jobs/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "JOB_NOT_FOUND"
