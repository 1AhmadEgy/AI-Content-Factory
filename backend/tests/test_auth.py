import os

from fastapi.testclient import TestClient

os.environ["AICF_API_KEY"] = "test-aicf-key"

from backend.main import app  # noqa: E402

client = TestClient(app)


def test_health_is_public():
    response = client.get("/health")
    assert response.status_code == 200


def test_protected_route_requires_key():
    response = client.get("/api/v1/auth/check")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_protected_route_rejects_invalid_key():
    response = client.get(
        "/api/v1/auth/check",
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401


def test_protected_route_accepts_valid_key():
    response = client.get(
        "/api/v1/auth/check",
        headers={"Authorization": "Bearer test-aicf-key"},
    )
    assert response.status_code == 200
    assert response.json() == {"data": {"authenticated": True}}


def test_projects_route_is_protected():
    response = client.get(
        "/api/v1/projects",
        headers={"Authorization": "Bearer test-aicf-key"},
    )
    assert response.status_code == 200
    assert response.json()["data"] == []
