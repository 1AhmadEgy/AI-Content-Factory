from __future__ import annotations

import base64
import binascii
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
        return _openai_compatible_request(
            endpoint=self.endpoint,
            request=request,
            timeout_seconds=self.timeout_seconds,
            headers={},
            error_prefix="LOCAL_PROVIDER",
        )

    def cancel(self, provider_run_id: str) -> bool:
        return False


class OpenAICompatibleCloudAdapter(ModelAdapter):
    """Real cloud adapter for providers exposing OpenAI-compatible chat completions."""

    def __init__(self, endpoint: str, api_key: str, capabilities: frozenset[str], timeout_seconds: int = 120) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self._capabilities = capabilities
        self.timeout_seconds = timeout_seconds

    def capability(self) -> ModelCapability:
        return ModelCapability(category="generation", capabilities=self._capabilities, runtime="CLOUD")

    def health_check(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(success=False, error_code="CLOUD_API_KEY_MISSING", error_message="Cloud provider API key is not configured")
        return _openai_compatible_request(
            endpoint=self.endpoint,
            request=request,
            timeout_seconds=self.timeout_seconds,
            headers={"Authorization": f"Bearer {self.api_key}"},
            error_prefix="CLOUD_PROVIDER",
        )

    def cancel(self, provider_run_id: str) -> bool:
        return False


class GeminiModelAdapter(ModelAdapter):
    """Real Google Gemini Developer API adapter using generateContent."""

    def __init__(self, api_key: str, model: str, capabilities: frozenset[str], timeout_seconds: int = 120) -> None:
        self.api_key = api_key
        self.model = model
        self._capabilities = capabilities
        self.timeout_seconds = timeout_seconds

    def capability(self) -> ModelCapability:
        return ModelCapability(category="generation", capabilities=self._capabilities, runtime="CLOUD")

    def health_check(self) -> bool:
        return bool(self.api_key and self.model)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(success=False, error_code="GEMINI_API_KEY_MISSING", error_message="GEMINI_API_KEY is not configured")
        prompt = request.parameters.get("prompt")
        messages = request.parameters.get("messages")
        if messages:
            parts = []
            for message in messages:
                role = message.get("role", "user")
                content = message.get("content", "")
                parts.append(f"{role}: {content}")
            prompt = "\n".join(parts)
        if not isinstance(prompt, str) or not prompt.strip():
            return ProviderResponse(success=False, error_code="GEMINI_EMPTY_PROMPT", error_message="Gemini request requires a non-empty prompt")
        payload: dict[str, object] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": request.parameters.get("temperature", 0.7)},
        }
        if request.seed is not None:
            payload["generationConfig"] = {**payload["generationConfig"], "seed": request.seed}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        try:
            req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            candidates = data.get("candidates") or []
            parts = ((candidates[0].get("content") or {}).get("parts") or []) if candidates else []
            text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
            if not text.strip():
                return ProviderResponse(success=False, error_code="GEMINI_EMPTY_TEXT", error_message="Gemini returned no text candidate")
            provider_run_id = data.get("responseId") or data.get("response_id")
            if not isinstance(provider_run_id, str) or not provider_run_id.strip():
                return ProviderResponse(success=False, error_code="GEMINI_RESPONSE_ID_MISSING", error_message="Gemini response did not include a response id")
            return ProviderResponse(success=True, output_text=text, provider_run_id=provider_run_id.strip(), metrics=data.get("usageMetadata", {}))
        except HTTPError as exc:
            return ProviderResponse(success=False, error_code="GEMINI_HTTP_ERROR", error_message=f"HTTP {exc.code}: {exc.reason}")
        except (URLError, OSError, json.JSONDecodeError, KeyError, IndexError, ValueError) as exc:
            return ProviderResponse(success=False, error_code="GEMINI_PROVIDER_ERROR", error_message=str(exc))

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
            if not body:
                return ProviderResponse(success=False, error_code="LOCAL_MEDIA_EMPTY_RESPONSE", error_message="Local media provider returned an empty response")
            if content_type == "application/json":
                return self._json_response(body, run_id)
            if not isinstance(run_id, str) or not run_id.strip():
                return ProviderResponse(success=False, error_code="LOCAL_MEDIA_RUN_ID_MISSING", error_message="Local media provider did not return a provider run id")
            return ProviderResponse(success=True, output_bytes=body, output_mime_type=content_type, provider_run_id=run_id.strip())
        except HTTPError as exc:
            return ProviderResponse(success=False, error_code="LOCAL_MEDIA_HTTP_ERROR", error_message=f"HTTP {exc.code}: {exc.reason}")
        except (URLError, OSError, json.JSONDecodeError, ValueError) as exc:
            return ProviderResponse(success=False, error_code="LOCAL_MEDIA_PROVIDER_ERROR", error_message=str(exc))

    @staticmethod
    def _json_response(body: bytes, provider_run_id: str | None) -> ProviderResponse:
        data = json.loads(body.decode("utf-8"))
        actual_run_id = provider_run_id or data.get("provider_run_id")
        if data.get("success") is False:
            return ProviderResponse(success=False, provider_run_id=actual_run_id, error_code=data.get("error_code", "LOCAL_MEDIA_ERROR"), error_message=data.get("error_message", "Local media provider failed"))
        if not isinstance(actual_run_id, str) or not actual_run_id.strip():
            return ProviderResponse(success=False, error_code="LOCAL_MEDIA_RUN_ID_MISSING", error_message="Local media provider did not return a provider run id")
        encoded = data.get("data") or data.get("output")
        if isinstance(encoded, str):
            try:
                raw = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error) as exc:
                return ProviderResponse(success=False, error_code="LOCAL_MEDIA_INVALID_RESPONSE", error_message=str(exc))
            if not raw:
                return ProviderResponse(success=False, error_code="LOCAL_MEDIA_EMPTY_OUTPUT", error_message="Local media provider returned empty output")
            return ProviderResponse(success=True, output_bytes=raw, output_mime_type=data.get("mime_type", data.get("mimeType", "application/octet-stream")), output_filename=data.get("filename"), output_metadata=data.get("metadata", {}), provider_run_id=actual_run_id.strip(), metrics=data.get("metrics", {}))
        text = data.get("text")
        if isinstance(text, str) and text.strip():
            return ProviderResponse(success=True, output_text=text, provider_run_id=actual_run_id.strip(), metrics=data.get("metrics", {}))
        return ProviderResponse(success=False, error_code="LOCAL_MEDIA_INVALID_RESPONSE", error_message="Expected non-empty base64 data or text in JSON response")

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


def _openai_compatible_request(*, endpoint: str, request: ProviderRequest, timeout_seconds: int, headers: dict[str, str], error_prefix: str) -> ProviderResponse:
    messages = request.parameters.get("messages") or [{"role": "user", "content": request.parameters.get("prompt", "")}]
    payload: dict[str, object] = {"model": request.model, "messages": messages, "temperature": request.parameters.get("temperature", 0.7), "stream": False}
    if request.seed is not None:
        payload["seed"] = request.seed
    if request.parameters.get("response_format") == "json":
        payload["response_format"] = {"type": "json_object"}
    if not any(isinstance(m, dict) and str(m.get("content", "")).strip() for m in messages):
        return ProviderResponse(success=False, error_code=f"{error_prefix}_EMPTY_PROMPT", error_message="Provider request requires non-empty messages")
    try:
        req = Request(endpoint + "/v1/chat/completions", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json", **headers}, method="POST")
        with urlopen(req, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = data["choices"][0]["message"]["content"]
        provider_run_id = data.get("id")
        if not isinstance(text, str) or not text.strip():
            return ProviderResponse(success=False, error_code=f"{error_prefix}_EMPTY_TEXT", error_message="Provider returned no text")
        if not isinstance(provider_run_id, str) or not provider_run_id.strip():
            return ProviderResponse(success=False, error_code=f"{error_prefix}_RUN_ID_MISSING", error_message="Provider did not return a run id")
        return ProviderResponse(success=True, output_text=text, provider_run_id=provider_run_id.strip(), metrics=data.get("usage", {}))
    except HTTPError as exc:
        return ProviderResponse(success=False, error_code=f"{error_prefix}_HTTP_ERROR", error_message=f"HTTP {exc.code}: {exc.reason}")
    except (KeyError, IndexError, json.JSONDecodeError, OSError, URLError, ValueError) as exc:
        return ProviderResponse(success=False, error_code=f"{error_prefix}_ERROR", error_message=str(exc))
