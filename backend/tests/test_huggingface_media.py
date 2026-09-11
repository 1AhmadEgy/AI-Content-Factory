import json
from types import SimpleNamespace

from backend.app.providers.contracts import ProviderRequest
from backend.app.providers.huggingface_media import HuggingFaceMediaAdapter


class FakeResponse:
    def __init__(self, body: bytes, content_type: str, request_id: str | None = None):
        self._body = body
        self.headers = {"Content-Type": content_type}
        if request_id:
            self.headers["x-request-id"] = request_id

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body


def _adapter():
    return HuggingFaceMediaAdapter(
        token="hf-test",
        model="test-model",
        task="text-to-image",
        capabilities=frozenset({"image"}),
        timeout_seconds=10,
    )


def test_empty_prompt_is_rejected():
    result = _adapter().execute(ProviderRequest(model="test-model", parameters={"prompt": "  "}))
    assert not result.success
    assert result.error_code == "HF_EMPTY_PROMPT"


def test_empty_provider_response_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "backend.app.providers.huggingface_media.urlopen",
        lambda request, timeout: FakeResponse(b"", "image/png", "run-1"),
    )
    result = _adapter().execute(ProviderRequest(model="test-model", parameters={"prompt": "a real scene"}))
    assert not result.success
    assert result.error_code == "HF_EMPTY_OUTPUT"


def test_json_provider_error_is_not_treated_as_media(monkeypatch):
    body = json.dumps({"error": "model unavailable"}).encode()
    monkeypatch.setattr(
        "backend.app.providers.huggingface_media.urlopen",
        lambda request, timeout: FakeResponse(body, "application/json", "run-1"),
    )
    result = _adapter().execute(ProviderRequest(model="test-model", parameters={"prompt": "a real scene"}))
    assert not result.success
    assert result.error_code == "HF_PROVIDER_ERROR"
    assert result.provider_run_id == "run-1"


def test_binary_without_provider_request_id_is_rejected(monkeypatch):
    monkeypatch.setattr(
        "backend.app.providers.huggingface_media.urlopen",
        lambda request, timeout: FakeResponse(b"PNG-BYTES", "image/png"),
    )
    result = _adapter().execute(ProviderRequest(model="test-model", parameters={"prompt": "a real scene"}))
    assert not result.success
    assert result.error_code == "HF_RUN_ID_MISSING"


def test_binary_with_real_provider_request_id_succeeds(monkeypatch):
    monkeypatch.setattr(
        "backend.app.providers.huggingface_media.urlopen",
        lambda request, timeout: FakeResponse(b"PNG-BYTES", "image/png", "hf-request-123"),
    )
    result = _adapter().execute(
        ProviderRequest(
            model="test-model",
            parameters={
                "prompt": "a real scene",
                "character_ids": ["char-1"],
                "location_ids": ["loc-1"],
                "country_id": "LY",
                "library_id": "lib-1",
                "continuity_rules": ["preserve identity"],
                "production_context": {"season": "1"},
                "width": 512,
            },
            seed=42,
        )
    )
    assert result.success
    assert result.provider_run_id == "hf-request-123"
    assert result.output_bytes == b"PNG-BYTES"
    assert result.output_mime_type == "image/png"
    assert result.output_metadata == {"task": "text-to-image"}


def test_continuity_context_is_not_sent_to_external_payload(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse(b"PNG-BYTES", "image/png", "hf-request-123")

    monkeypatch.setattr("backend.app.providers.huggingface_media.urlopen", fake_urlopen)
    _adapter().execute(
        ProviderRequest(
            model="test-model",
            parameters={
                "prompt": "a real scene",
                "character_ids": ["char-1"],
                "location_ids": ["loc-1"],
                "country_id": "LY",
                "library_id": "lib-1",
                "continuity_rules": ["preserve identity"],
                "production_context": {"season": "1"},
                "width": 512,
            },
            seed=42,
        )
    )
    provider_payload = captured["payload"]
    assert provider_payload["inputs"] == "a real scene"
    assert provider_payload["parameters"] == {"width": 512, "seed": 42}
    assert all(key not in provider_payload for key in ("character_ids", "location_ids", "country_id", "library_id", "continuity_rules", "production_context"))
