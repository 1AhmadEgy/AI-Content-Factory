from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class OpenAIProviderError(RuntimeError):
    pass


class OpenAIModelAdapter(ModelAdapter):
    """Real OpenAI HTTP adapter. Provider failures never produce synthetic assets."""

    def __init__(self, model_id: str, category: str, api_key: str | None = None, base_url: str | None = None) -> None:
        self.model_id = model_id
        self.category = category.upper()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")

    def capability(self) -> ModelCapability:
        return ModelCapability(
            category="generation",
            capabilities=frozenset({"generation", self.category.lower(), "real-provider"}),
            runtime="CLOUD",
            license_status="CONFIGURED",
        )

    def health_check(self) -> bool:
        return bool(self.api_key)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(False, error_code="OPENAI_API_KEY_MISSING", error_message="OPENAI_API_KEY is not configured")
        try:
            if self.category == "IMAGE":
                return self._image(request)
            if self.category == "TTS":
                return self._tts(request)
            return self._text(request)
        except OpenAIProviderError as exc:
            return ProviderResponse(False, error_code="OPENAI_REQUEST_FAILED", error_message=str(exc))

    def _request(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            f"{self.base_url}/{endpoint.lstrip('/')}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=float(os.getenv("AICF_PROVIDER_TIMEOUT_SECONDS", "120"))) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OpenAIProviderError(f"HTTP {exc.code}: {detail[:2000]}") from exc
        except urllib.error.URLError as exc:
            raise OpenAIProviderError(f"network error: {exc.reason}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OpenAIProviderError("provider returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise OpenAIProviderError("provider returned an invalid response")
        return data

    def _text(self, request: ProviderRequest) -> ProviderResponse:
        prompt = str(request.parameters.get("prompt", "")).strip()
        if not prompt:
            return ProviderResponse(False, error_code="PROMPT_REQUIRED", error_message="prompt is required")
        payload: dict[str, Any] = {"model": request.model, "input": prompt}
        data = self._request("responses", payload)
        output_text = data.get("output_text")
        if not output_text:
            parts: list[str] = []
            for item in data.get("output", []) or []:
                if not isinstance(item, dict):
                    continue
                for content in item.get("content", []) or []:
                    if isinstance(content, dict) and content.get("text"):
                        parts.append(str(content["text"]))
            output_text = "\n".join(parts).strip()
        if not output_text:
            raise OpenAIProviderError("text response contained no output")
        return ProviderResponse(True, output_text=output_text, provider_run_id=str(data.get("id") or uuid.uuid4()))

    def _image(self, request: ProviderRequest) -> ProviderResponse:
        prompt = str(request.parameters.get("prompt") or request.parameters.get("description") or "").strip()
        if not prompt:
            return ProviderResponse(False, error_code="PROMPT_REQUIRED", error_message="prompt is required")
        payload: dict[str, Any] = {"model": request.model, "prompt": prompt, "n": 1}
        for key in ("size", "quality", "background", "output_format"):
            if key in request.parameters:
                payload[key] = request.parameters[key]
        data = self._request("images/generations", payload)
        item = (data.get("data") or [{}])[0]
        if item.get("b64_json"):
            raw = base64.b64decode(item["b64_json"])
            fmt = str(payload.get("output_format", "png"))
            return ProviderResponse(True, output_bytes=raw, output_mime_type=f"image/{fmt}", output_filename=f"generated-image.{fmt}", provider_run_id=str(data.get("id") or uuid.uuid4()))
        url = item.get("url")
        if not url:
            raise OpenAIProviderError("image response contained neither b64_json nor url")
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                raw = response.read()
                mime = response.headers.get_content_type() or "image/png"
        except (urllib.error.URLError, OSError) as exc:
            raise OpenAIProviderError(f"image download failed: {exc}") from exc
        return ProviderResponse(True, output_bytes=raw, output_mime_type=mime, output_filename="generated-image", provider_run_id=str(data.get("id") or uuid.uuid4()))

    def _tts(self, request: ProviderRequest) -> ProviderResponse:
        text = str(request.parameters.get("text") or request.parameters.get("narration") or "").strip()
        if not text:
            return ProviderResponse(False, error_code="TEXT_REQUIRED", error_message="text or narration is required")
        fmt = str(request.parameters.get("response_format", "mp3"))
        payload = {"model": request.model, "voice": str(request.parameters.get("voice", "alloy")), "input": text, "response_format": fmt}
        req = urllib.request.Request(
            f"{self.base_url}/audio/speech",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = response.read()
                mime = response.headers.get_content_type() or "audio/mpeg"
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OpenAIProviderError(f"HTTP {exc.code}: {detail[:2000]}") from exc
        except urllib.error.URLError as exc:
            raise OpenAIProviderError(f"network error: {exc.reason}") from exc
        return ProviderResponse(True, output_bytes=raw, output_mime_type=mime, output_filename=f"speech.{fmt}", provider_run_id=str(uuid.uuid4()))

    def cancel(self, provider_run_id: str) -> bool:
        return False
