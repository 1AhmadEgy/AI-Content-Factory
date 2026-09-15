from fastapi.testclient import TestClient

from app.main import app


# Use a concrete application endpoint that is registered by a router so this
# test verifies authentication independently of FastAPI's documentation routes.
PROTECTED_PATH = "/api/v1/projects"


def test_missing_api_key_is_rejected(monkeypatch):
    monkeypatch.setenv("AICF_API_KEY", "test-aicf-key")
    monkeypatch.setenv("AICF_TEST_MODE", "false")
    response = TestClient(app).get(PROTECTED_PATH)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_api_key_is_rejected(monkeypatch):
    monkeypatch.setenv("AICF_API_KEY", "test-aicf-key")
    monkeypatch.setenv("AICF_TEST_MODE", "false")
    response = TestClient(app).get(
        PROTECTED_PATH,
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_valid_api_key_is_accepted(monkeypatch):
    monkeypatch.setenv("AICF_API_KEY", "test-aicf-key")
    monkeypatch.setenv("AICF_TEST_MODE", "false")
    response = TestClient(app).get(
        PROTECTED_PATH,
        headers={"Authorization": "Bearer test-aicf-key"},
    )
    assert response.status_code == 200
    assert "data" in response.json()


def test_health_remains_public(monkeypatch):
    monkeypatch.setenv("AICF_API_KEY", "test-aicf-key")
    monkeypatch.setenv("AICF_TEST_MODE", "false")
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200


def test_missing_server_key_fails_closed(monkeypatch):
    monkeypatch.delenv("AICF_API_KEY", raising=False)
    monkeypatch.setenv("AICF_TEST_MODE", "false")
    response = TestClient(app).get(PROTECTED_PATH)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_NOT_CONFIGURED"


def test_android_authorization_header_shape_is_accepted(monkeypatch):
    monkeypatch.setenv("AICF_API_KEY", "android-backend-key")
    monkeypatch.setenv("AICF_TEST_MODE", "false")
    response = TestClient(app).get(
        PROTECTED_PATH,
        headers={"Authorization": "Bearer android-backend-key"},
    )
    assert response.status_code == 200
