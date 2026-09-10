from __future__ import annotations

import base64
import json

from backend.app.providers.contracts import ProviderRequest
from backend.app.providers.local_media import LocalMediaModelAdapter


class _Response:
    def __init__(self, body: bytes, content_type: str = "application/json") -> None:
        self._body = body
        self.headers = {"Content-Type": content_type, "X-Provider-Run-Id": "run-123"}

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_local_media_adapter_decodes_base64(monkeypatch):
    payload = {"data": base64.b64encode(b"PNG-DATA").decode(), "mime_type": "image/png", "filename": "shot.png"}
    monkeypatch.setattr("backend.app.providers.local_media.urlopen", lambda *args, **kwargs: _Response(json.dumps(payload).encode()))
    adapter = LocalMediaModelAdapter("http://127.0.0.1:8188/generate", frozenset({"image"}))
    response = adapter.execute(ProviderRequest(model="local-image", parameters={"prompt": "test"}, seed=7))
    assert response.success is True
    assert response.output_bytes == b"PNG-DATA"
    assert response.output_mime_type == "image/png"
    assert response.output_filename == "shot.png"
    assert response.provider_run_id == "run-123"


def test_local_media_adapter_accepts_raw_binary(monkeypatch):
    monkeypatch.setattr("backend.app.providers.local_media.urlopen", lambda *args, **kwargs: _Response(b"VIDEO-DATA", "video/mp4"))
    adapter = LocalMediaModelAdapter("http://127.0.0.1:9000/generate", frozenset({"video"}))
    response = adapter.execute(ProviderRequest(model="local-video", parameters={"duration": 4}))
    assert response.success is True
    assert response.output_bytes == b"VIDEO-DATA"
    assert response.output_mime_type == "video/mp4"


def test_local_media_adapter_reports_invalid_json(monkeypatch):
    monkeypatch.setattr("backend.app.providers.local_media.urlopen", lambda *args, **kwargs: _Response(b"{}"))
    adapter = LocalMediaModelAdapter("http://127.0.0.1:9000/generate", frozenset({"audio"}))
    response = adapter.execute(ProviderRequest(model="local-audio"))
    assert response.success is False
    assert response.error_code == "LOCAL_MEDIA_INVALID_RESPONSE"
