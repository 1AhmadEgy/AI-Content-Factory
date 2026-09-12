from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_pipeline_api_fails_closed_without_real_video():
    response = client.post(
        "/api/v1/pipeline/run",
        json={
            "project_id": "project-1",
            "assets": [
                {"asset_id": "a1", "readable": True, "size_bytes": 10, "license_status": "VERIFIED"}
            ],
            "candidates": [
                {"asset_id": "a1", "qc_score": 1.0, "semantic_score": 1.0, "continuity_score": 1.0, "technical_score": 1.0}
            ],
            "duration_us": 1_000_000,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["qcPassed"] is False
    assert body["bestAssetId"] == "a1"
    assert body["renderedPath"] is None
    assert "TIMELINE_HAS_NO_VIDEO" in body["errors"]
