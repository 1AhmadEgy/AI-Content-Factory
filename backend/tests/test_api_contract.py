from fastapi.testclient import TestClient

from app.main import app


def test_health_uses_standard_envelope_and_request_id() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health", headers={"X-Request-Id": "req_test"})

    assert response.status_code == 200
    assert response.json() == {
        "data": {"status": "OK", "service": "ai-content-factory-backend"},
        "requestId": "req_test",
    }
    assert response.headers["X-Request-Id"] == "req_test"


def test_http_errors_use_standard_error_envelope() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/projects/missing", headers={"X-Request-Id": "req_error"})

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "PROJECT_NOT_FOUND"
    assert body["error"]["requestId"] == "req_error"
    assert "detail" not in body


def test_validation_errors_map_to_400() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/projects", json={"name": ""}, headers={"X-Request-Id": "req_validation"})

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["requestId"] == "req_validation"
    assert body["error"]["details"]["errors"]
