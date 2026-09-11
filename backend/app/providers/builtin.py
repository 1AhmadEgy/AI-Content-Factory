from __future__ import annotations

import base64
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class LocalModelAdapter(ModelAdapter):
    """OpenAI-compatible local HTTP adapter for text generation."""

    def __init__(self, endpoint: str, capabilities: frozenset[str], timeout_seconds: int = 120) -> None:
        self.endpoint = endpoint.rstrip("/")
        self._capabilities = capabilities
        self.timeout_seconds = timeout_seconds

    def capability(self) -> ModelCapability:
        return ModelCapability(category="generation", capabilities=self._capabilities, runtime="LOCAL", license_status="OPEN")

    def health_check(self) -> bool:
        return bool(self.endpoint)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        messages = request.parameters.get("messages") or [{"role": "user", "content": request.parameters.get("prompt", "")}]
        payload = {
            "model": request.model,
            "messages": messages,
            "temperature": request.parameters.get("temperature", 0.7),
            "stream": False,
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        if request.parameters.get("response_format") == "json":
            payload["response_format"] = {"type": "json_object"}
        try:
            req = Request(
                self.endpoint + "/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"]
            return ProviderResponse(
                success=True,
                output_text=text,
                provider_run_id=str(data.get("id") or "local-text"),
                metrics={"local": 1.0},
            )
        except HTTPError as exc:
            return ProviderResponse(success=False, error_code="LOCAL_PROVIDER_HTTP_ERROR", error_message=f"HTTP {exc.code}: {exc.reason}")
        except (KeyError, IndexError, json.JSONDecodeError, OSError, URLError, ValueError) as exc:
            return ProviderResponse(success=False, error_code="LOCAL_PROVIDER_ERROR", error_message=str(exc))

    def cancel(self, provider_run_id: str) -> bool:
        return False


class LocalMediaModelAdapter(ModelAdapter):
    """Configurable local HTTP adapter for real image/video/audio generation services."""

    def __init__(self, endpoint: str, capabilities: frozenset[str], timeout_seconds: int = 300, headers: dict[str, str] | None = None) -> None:
        self.endpoint = endpoint.rstrip("/")
        self._capabilities = capabilities
        self.timeout_seconds = timeout_seconds
        self.headers = {"Content-Type": "application/json", **(headers or {})}

    def capability(self) -> ModelCapability:
        return ModelCapability(category="generation", capabilities=self._capabilities, runtime="LOCAL", license_status="OPEN")

    def health_check(self) -> bool:
        return bool(self.endpoint)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        payload = {"model": request.model, "parameters": request.parameters}
        if request.seed is not None:
            payload["seed"] = request.seed
        try:
            req = Request(self.endpoint, data=json.dumps(payload).encode("utf-8"), headers=self.headers, method="POST")
            with urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "application/octet-stream").split(";", 1)[0].strip()
                run_id = response.headers.get("X-Provider-Run-Id")
            if content_type == "application/json":
                return self._json_response(body, run_id)
            return ProviderResponse(success=True, output_bytes=body, output_mime_type=content_type, provider_run_id=run_id or "local-media", metrics={"local": 1.0, "binary": 1.0})
        except HTTPError as exc:
            return ProviderResponse(success=False, error_code="LOCAL_MEDIA_HTTP_ERROR", error_message=f"HTTP {exc.code}: {exc.reason}")
        except (URLError, OSError, json.JSONDecodeError, ValueError) as exc:
            return ProviderResponse(success=False, error_code="LOCAL_MEDIA_PROVIDER_ERROR", error_message=str(exc))

    @staticmethod
    def _json_response(body: bytes, provider_run_id: str | None) -> ProviderResponse:
        data = json.loads(body.decode("utf-8"))
        if data.get("success") is False:
            return ProviderResponse(
                success=False,
                provider_run_id=provider_run_id or data.get("provider_run_id"),
                error_code=data.get("error_code", "LOCAL_MEDIA_ERROR"),
                error_message=data.get("error_message", "Local media provider failed"),
            )
        encoded = data.get("data") or data.get("output")
        if isinstance(encoded, str):
            try:
                raw = base64.b64decode(encoded, validate=True)
            except (ValueError, base64.binascii.Error) as exc:
                return ProviderResponse(success=False, error_code="LOCAL_MEDIA_INVALID_RESPONSE", error_message=str(exc))
            return ProviderResponse(
                success=True,
                output_bytes=raw,
                output_mime_type=data.get("mime_type", data.get("mimeType", "application/octet-stream")),
                output_filename=data.get("filename"),
                output_metadata=data.get("metadata", {}),
                provider_run_id=provider_run_id or data.get("provider_run_id") or "local-media",
                metrics=data.get("metrics", {}),
            )
        if data.get("text") is not None:
            return ProviderResponse(success=True, output_text=str(data["text"]), provider_run_id=provider_run_id or "local-media", metrics=data.get("metrics", {}))
        return ProviderResponse(success=False, error_code="LOCAL_MEDIA_INVALID_RESPONSE", error_message="Expected base64 data or text in JSON response")

    def cancel(self, provider_run_id: str) -> bool:
        return False


class CloudModelAdapter(ModelAdapter):
    """Explicit cloud adapter contract; no hidden or simulated network calls."""

    def __init__(self, provider_name: str, capabilities: frozenset[str] | None = None) -> None:
        self.provider_name = provider_name
        self._capabilities = capabilities or frozenset()

    def capability(self) -> ModelCapability:
        return ModelCapability(category="generation", capabilities=self._capabilities, runtime="CLOUD")

    def health_check(self) -> bool:
        return bool(self.provider_name)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(success=False, error_code="CLOUD_ADAPTER_NOT_CONFIGURED", error_message=f"Configure adapter for {self.provider_name}")

    def cancel(self, provider_run_id: str) -> bool:
        return False
