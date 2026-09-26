from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class ElevenLabsTTSAdapter(ModelAdapter):
    """ElevenLabs Text-to-Speech adapter.

    The API key stays server-side. A voice id is supplied through the job
    parameters or AICF_ELEVENLABS_VOICE_ID, while the existing asset/provenance
    pipeline persists the returned audio bytes.
    """

    _BASE_URL = "https://api.elevenlabs.io/v1"
    _CAPABILITIES = frozenset({"tts", "voice", "speech", "arabic", "character-voice"})

    def __init__(
        self,
        model_id: str = "eleven_multilingual_v2",
        api_key: str | None = None,
        default_voice_id: str | None = None,
        timeout_seconds: int = 120,
    ) -> None:
        self.model_id = model_id.strip() or "eleven_multilingual_v2"
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY", "")
        self.default_voice_id = default_voice_id or os.getenv("AICF_ELEVENLABS_VOICE_ID", "")
        self.timeout_seconds = max(15, timeout_seconds)

    def capability(self) -> ModelCapability:
        return ModelCapability(
            category="generation",
            capabilities=self._CAPABILITIES,
            runtime="CLOUD",
            license_status="CONFIGURED",
        )

    def health_check(self) -> bool:
        return bool(self.api_key)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(False, error_code="ELEVENLABS_API_KEY_MISSING")

        parameters = dict(request.parameters)
        text = parameters.pop("text", parameters.pop("prompt", ""))
        if not isinstance(text, str) or not text.strip():
            return ProviderResponse(False, error_code="ELEVENLABS_TEXT_REQUIRED")

        voice_id = str(parameters.pop("voice_id", "") or self.default_voice_id).strip()
        if not voice_id:
            return ProviderResponse(False, error_code="ELEVENLABS_VOICE_ID_REQUIRED")

        model = str(parameters.pop("model", "") or request.model or self.model_id)
        output_format = str(parameters.pop("output_format", "mp3_44100_128"))

        payload: dict[str, object] = {
            "text": text,
            "model_id": model,
        }

        # Multilingual v2 determines language from the text/voice and does not
        # accept language_code. Other supported models may accept it.
        language_code = parameters.pop("language_code", None)
        if language_code and model != "eleven_multilingual_v2":
            payload["language_code"] = language_code

        voice_settings = parameters.pop("voice_settings", None)
        if isinstance(voice_settings, dict):
            payload["voice_settings"] = voice_settings

        try:
            url = f"{self._BASE_URL}/text-to-speech/{voice_id}?output_format={output_format}"
            request_http = Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg,audio/*",
                },
                method="POST",
            )
            with urlopen(request_http, timeout=self.timeout_seconds) as response:
                audio = response.read()
                content_type = response.headers.get("Content-Type", "audio/mpeg").split(";", 1)[0].strip()
                request_id = response.headers.get("request-id")

            if not audio:
                return ProviderResponse(False, error_code="ELEVENLABS_EMPTY_AUDIO")

            metadata = {
                "provider": "elevenlabs",
                "model": model,
                "voiceId": voice_id,
                "language": language_code or "ar",
                "dialect": parameters.get("dialect", "arabic"),
            }
            if request_id:
                metadata["requestId"] = request_id

            return ProviderResponse(
                True,
                output_bytes=audio,
                output_mime_type=content_type or "audio/mpeg",
                output_filename=f"elevenlabs-{voice_id}.mp3",
                output_metadata=metadata,
                provider_run_id=request_id or f"elevenlabs:{voice_id}",
            )
        except HTTPError as exc:
            return ProviderResponse(
                False,
                error_code="ELEVENLABS_HTTP_ERROR",
                error_message=f"HTTP {exc.code}: {exc.reason}",
            )
        except (OSError, URLError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return ProviderResponse(
                False,
                error_code="ELEVENLABS_PROVIDER_ERROR",
                error_message=str(exc)[:500],
            )

    def cancel(self, provider_run_id: str) -> bool:
        # The synchronous TTS endpoint has no provider task to cancel.
        return False
