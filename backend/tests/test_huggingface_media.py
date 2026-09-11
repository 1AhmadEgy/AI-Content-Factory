import json

from backend.app.providers.contracts import ProviderRequest
from backend.app.providers.huggingface_media import HuggingFaceMediaAdapter


class FakeResponse:
    def __init__(self, body: bytes, content_type: str, request_id: str | None = None, header_name: str = "x-request-id"):
        self._body = body
        self.headers = {"Content-Type": content_type}
        if request_id:
            self.headers[header_name] = request_id

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body


def _adapter(task: str = "text-to-image", capability: str = "image"):
    return HuggingFaceMediaAdapter(
        token="hf-test",
        model="test-model",
        task=task,
        capabilities=frozenset({capability}),
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


def test_binary_without_provider_request_id_is_still_real_success(monkeypatch):
    monkeypatch.setattr(
        "backend.app.providers.huggingface_media.urlopen",
        lambda request, timeout: FakeResponse(b"PNG-BYTES", "image/png"),
    )
    result = _adapter().execute(ProviderRequest(model="test-model", parameters={"prompt": "a real scene"}))
    assert result.success
    assert result.provider_run_id is None
    assert result.output_bytes == b"PNG-BYTES"
    assert result.output_mime_type == "image/png"


def test_binary_with_x_request_id_succeeds(monkeypatch):
    monkeypatch.setattr(
        "backend.app.providers.huggingface_media.urlopen",
        lambda request, timeout: FakeResponse(b"PNG-BYTES", "image/png", "hf-request-123"),
    )
    result = _adapter().execute(ProviderRequest(model="test-model", parameters={"prompt": "a real scene"}))
    assert result.success
    assert result.provider_run_id == "hf-request-123"
    assert result.output_bytes == b"PNG-BYTES"
    assert result.output_mime_type == "image/png"
    assert result.output_metadata == {"task": "text-to-image", "model": "test-model"}


def test_binary_with_documented_inference_id_succeeds(monkeypatch):
    monkeypatch.setattr(
        "backend.app.providers.huggingface_media.urlopen",
        lambda request, timeout: FakeResponse(b"PNG-BYTES", "image/png", "inference-123", "Inference-Id"),
    )
    result = _adapter().execute(ProviderRequest(model="test-model", parameters={"prompt": "a real scene"}))
    assert result.success
    assert result.provider_run_id == "inference-123"


def test_text_to_video_uses_binary_video_response(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse(b"MP4-BYTES", "video/mp4", "video-run-1")

    monkeypatch.setattr("backend.app.providers.huggingface_media.urlopen", fake_urlopen)
    result = _adapter("text-to-video", "video").execute(
        ProviderRequest(model="test-model", parameters={"prompt": "a real moving scene", "num_frames": 16})
    )
    assert result.success
    assert result.output_mime_type == "video/mp4"
    assert result.provider_run_id == "video-run-1"
    assert captured["payload"] == {"inputs": "a real moving scene", "parameters": {"num_frames": 16}}


def test_text_to_speech_uses_binary_audio_response(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse(b"AUDIO-BYTES", "audio/flac", "tts-run-1")

    monkeypatch.setattr("backend.app.providers.huggingface_media.urlopen", fake_urlopen)
    result = _adapter("text-to-speech", "tts").execute(
        ProviderRequest(model="test-model", parameters={"prompt": "Hello from the factory", "voice": "af_nicole"})
    )
    assert result.success
    assert result.output_mime_type == "audio/flac"
    assert result.provider_run_id == "tts-run-1"
    assert captured["payload"] == {"inputs": "Hello from the factory", "parameters": {"voice": "af_nicole"}}


def test_continuity_context_is_not_sent_to_external_payload(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse(b"PNG-BYTES", "image/png", "hf-request-123")

    monkeypatch.setattr("backend.app.providers.huggingface_media.urlopen", fake_urlopen)
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
    assert result.output_metadata == {"task": "text-to-image", "model": "test-model"}
    provider_payload = captured["payload"]
    assert provider_payload["inputs"] == "a real scene"
    assert provider_payload["parameters"] == {"width": 512, "seed": 42}
    assert all(key not in provider_payload for key in ("character_ids", "location_ids", "country_id", "library_id", "continuity_rules", "production_context"))
