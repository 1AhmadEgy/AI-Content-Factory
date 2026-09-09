import os

os.environ["AICF_DATABASE_PATH"] = ":memory:"

from fastapi.testclient import TestClient

from backend.app.main import app


def test_create_project_then_job() -> None:
    client = TestClient(app)
    project_response = client.post("/api/v1/projects", json={"name": "Demo"})
    assert project_response.status_code == 201
    project_id = project_response.json()["data"]["id"]

    job_response = client.post(
        "/api/v1/jobs",
        json={
            "projectId": project_id,
            "type": "IMAGE",
            "targetType": "shot",
            "input": {"parameters": {"prompt": "hello"}, "deterministic": True},
        },
    )
    assert job_response.status_code == 202
    job_id = job_response.json()["data"]["id"]
    assert job_response.json()["data"]["status"] == "QUEUED"

    get_response = client.get(f"/api/v1/jobs/{job_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == job_id


def test_get_missing_job() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/jobs/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "JOB_NOT_FOUND"
