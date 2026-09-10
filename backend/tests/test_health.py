from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "OK"
    assert response.json()["requestId"]


def test_readiness() -> None:
    response = client.get("/api/v1/readiness")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "READY"
    assert response.json()["requestId"]
