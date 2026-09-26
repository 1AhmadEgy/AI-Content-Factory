import os

from fastapi.testclient import TestClient

from app.main import app


def test_health_is_public():
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_protected_endpoint_requires_bearer_token(monkeypatch):
    monkeypatch.setenv("AICF_API_KEY", "test-api-key")
    monkeypatch.setenv("AICF_TEST_MODE", "false")

    client = TestClient(app)
    response = client.get("/api/v1/projects")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_protected_endpoint_rejects_wrong_token(monkeypatch):
    monkeypatch.setenv("AICF_API_KEY", "test-api-key")
    monkeypatch.setenv("AICF_TEST_MODE", "false")

    client = TestClient(app)
    response = client.get(
        "/api/v1/projects",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


def test_protected_endpoint_accepts_configured_token(monkeypatch):
    monkeypatch.setenv("AICF_API_KEY", "test-api-key")
    monkeypatch.setenv("AICF_TEST_MODE", "false")

    client = TestClient(app)
    response = client.get(
        "/api/v1/projects",
        headers={"Authorization": "Bearer test-api-key"},
    )
    assert response.status_code == 200
    assert "data" in response.json()
