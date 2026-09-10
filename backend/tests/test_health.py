from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["data"]["status"] == "OK"
    assert payload["data"]["service"] == "ai-content-factory-backend"


def test_readiness() -> None:
    response = client.get("/api/v1/readiness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["data"]["status"] == "READY"
