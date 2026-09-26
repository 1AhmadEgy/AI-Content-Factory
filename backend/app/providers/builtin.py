from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class LocalModelAdapter(ModelAdapter):
    """OpenAI-compatible local HTTP adapter for text generation only."""

    _SUPPORTED_CAPABILITIES = frozenset({"text", "story", "script", "scene", "shot", "character", "world"})

    def __init__(self, endpoint: str, capabilities: frozenset[str] | None = None, timeout_seconds: int = 120) -> None:
        self.endpoint = endpoint.rstrip("/")
        requested = capabilities or frozenset()
        self._capabilities = requested & self._SUPPORTED_CAPABILITIES
        self.timeout_seconds = timeout_seconds

    def capability(self) -> ModelCapability:
        return ModelCapability(category="generation", capabilities=self._capabilities, runtime="LOCAL", license_status="OPEN")

    def health_check(self) -> bool:
        return bool(self.endpoint)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        messages = request.parameters.get("messages") or [{"role": "user", "content": request.parameters.get("prompt", "")}]
        payload = {"model": request.model, "messages": messages, "temperature": request.parameters.get("temperature", 0.7), "stream": False}
        if request.seed is not None:
            payload["seed"] = request.seed
        if request.parameters.get("response_format") == "json":
            payload["response_format"] = {"type": "json_object"}
        try:
            req = Request(self.endpoint + "/v1/chat/completions", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                return ProviderResponse(success=False, error_code="LOCAL_EMPTY_TEXT", error_message="Local provider returned no text")
            return ProviderResponse(success=True, output_text=text, provider_run_id=str(data.get("id") or "local"), metrics={"local": 1.0})
        except (KeyError, IndexError, json.JSONDecodeError, OSError, URLError) as exc:
            return ProviderResponse(success=False, error_code="LOCAL_PROVIDER_ERROR", error_message=str(exc))

    def cancel(self, provider_run_id: str) -> bool:
        return False


class AIMLAPIModelAdapter(ModelAdapter):
    """OpenAI-compatible AIMLAPI text adapter with a fixed provider endpoint."""

    _CAPABILITIES = frozenset({"generation", "text", "story", "script", "scene", "shot", "character", "world", "real-provider"})

    def __init__(self, model_id: str, api_key: str | None = None, timeout_seconds: int = 120) -> None:
        import os
        self.model_id = model_id
        self.api_key = api_key or os.getenv("AIMLAPI_API_KEY", "")
        self.timeout_seconds = timeout_seconds

    def capability(self) -> ModelCapability:
        return ModelCapability(category="generation", capabilities=self._CAPABILITIES, runtime="CLOUD", license_status="CONFIGURED")

    def health_check(self) -> bool:
        return bool(self.api_key)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        import os
        if not self.api_key:
            return ProviderResponse(False, error_code="AIMLAPI_API_KEY_MISSING")
        messages = request.parameters.get("messages") or [{"role": "user", "content": request.parameters.get("prompt", "")}]
        payload = {"model": request.model, "messages": messages}
        for key in ("temperature", "top_p", "max_tokens", "response_format", "tools", "tool_choice"):
            if key in request.parameters:
                payload[key] = request.parameters[key]
        try:
            req = Request(
                "https://api.aimlapi.com/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=int(os.getenv("AICF_PROVIDER_TIMEOUT_SECONDS", str(self.timeout_seconds)))) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"]
            if not isinstance(text, str) or not text.strip():
                return ProviderResponse(False, error_code="AIMLAPI_EMPTY_TEXT")
            usage = data.get("usage") or {}
            metrics = {}
            if usage.get("prompt_tokens") is not None:
                metrics["input_tokens"] = float(usage["prompt_tokens"])
            if usage.get("completion_tokens") is not None:
                metrics["output_tokens"] = float(usage["completion_tokens"])
            return ProviderResponse(True, output_text=text, provider_run_id=str(data.get("id") or "aimlapi"), metrics=metrics)
        except (KeyError, IndexError, json.JSONDecodeError, OSError, URLError) as exc:
            return ProviderResponse(False, error_code="AIMLAPI_PROVIDER_ERROR", error_message=str(exc)[:500])

    def cancel(self, provider_run_id: str) -> bool:
        return False



class LlamaGenVideoAdapter(ModelAdapter):
    """LlamaGen asynchronous video-generation adapter.

    LlamaGen creates an artwork asynchronously. The adapter submits a generation,
    then polls the documented artwork status endpoint until it reaches a terminal
    state. Provider URLs are fixed to prevent endpoint/SSRF configuration abuse.
    """

    _CAPABILITIES = frozenset({"video", "text-to-video", "image-to-video", "storyboard-to-video", "media", "generation"})

    def __init__(self, model_id: str = "", api_key: str | None = None, timeout_seconds: int = 300, poll_interval_seconds: int = 3) -> None:
        import os
        self.model_id = model_id.strip()
        self.api_key = api_key or os.getenv("LLAMAGEN_API_KEY", "")
        self.timeout_seconds = timeout_seconds
        self.poll_interval_seconds = max(1, poll_interval_seconds)

    def capability(self) -> ModelCapability:
        return ModelCapability(category="video", capabilities=self._CAPABILITIES, runtime="CLOUD", license_status="CONFIGURED")

    def health_check(self) -> bool:
        return bool(self.api_key)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        import os
        import time

        if not self.api_key:
            return ProviderResponse(False, error_code="LLAMAGEN_API_KEY_MISSING")

        params = dict(request.parameters)
        prompt = params.pop("prompt", "")
        if not isinstance(prompt, str) or not prompt.strip():
            return ProviderResponse(False, error_code="LLAMAGEN_PROMPT_REQUIRED")

        payload = dict(params)
        payload["prompt"] = prompt
        if request.seed is not None:
            payload["seed"] = request.seed
        if self.model_id and "model" not in payload:
            payload["model"] = self.model_id

        base = "https://api.llamagen.ai/v1"
        timeout = int(os.getenv("AICF_PROVIDER_TIMEOUT_SECONDS", str(self.timeout_seconds)))

        try:
            create = Request(
                base + "/artworks/generations",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(create, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))

            provider_id = self._extract_id(data)
            if not provider_id:
                return ProviderResponse(False, error_code="LLAMAGEN_INVALID_CREATE_RESPONSE", error_message="Generation response did not contain an artwork id")

            deadline = time.monotonic() + timeout
            last = data
            while time.monotonic() < deadline:
                state = self._status(last)
                if state in {"completed", "complete", "succeeded", "success", "done", "finished"}:
                    url = self._extract_media_url(last)
                    if url:
                        return ProviderResponse(
                            True,
                            output_metadata={"provider": "llamagen", "status": state, "remote_url": url},
                            provider_run_id=str(provider_id),
                        )
                    return ProviderResponse(True, provider_run_id=str(provider_id), output_metadata={"provider": "llamagen", "status": state, "response": last})

                if state in {"failed", "error", "cancelled", "canceled"}:
                    return ProviderResponse(False, provider_run_id=str(provider_id), error_code="LLAMAGEN_GENERATION_FAILED", error_message=self._extract_error(last))

                time.sleep(self.poll_interval_seconds)
                status_req = Request(
                    base + "/artworks/generations/" + str(provider_id),
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    method="GET",
                )
                with urlopen(status_req, timeout=min(timeout, 30)) as response:
                    last = json.loads(response.read().decode("utf-8"))

            return ProviderResponse(False, provider_run_id=str(provider_id), error_code="LLAMAGEN_POLL_TIMEOUT", error_message="Generation did not reach a terminal state before timeout")
        except HTTPError as exc:
            return ProviderResponse(False, error_code="LLAMAGEN_HTTP_ERROR", error_message=f"HTTP {exc.code}: {exc.reason}")
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, OSError, URLError, ValueError) as exc:
            return ProviderResponse(False, error_code="LLAMAGEN_PROVIDER_ERROR", error_message=str(exc)[:500])

    @staticmethod
    def _extract_id(data: object) -> str | None:
        if not isinstance(data, dict):
            return None
        for key in ("id", "generation_id", "artwork_id"):
            value = data.get(key)
            if value:
                return str(value)
        nested = data.get("data")
        if isinstance(nested, dict):
            return LlamaGenVideoAdapter._extract_id(nested)
        return None

    @staticmethod
    def _status(data: object) -> str:
        if not isinstance(data, dict):
            return "unknown"
        for key in ("status", "state"):
            value = data.get(key)
            if isinstance(value, str):
                return value.lower()
        nested = data.get("data")
        if isinstance(nested, dict):
            return LlamaGenVideoAdapter._status(nested)
        return "unknown"

    @staticmethod
    def _extract_media_url(data: object) -> str | None:
        if not isinstance(data, dict):
            return None
        for key in ("video_url", "url", "output_url", "download_url"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith(("https://", "http://")):
                return value
        for key in ("video", "output", "result", "data"):
            nested = data.get(key)
            if isinstance(nested, dict):
                found = LlamaGenVideoAdapter._extract_media_url(nested)
                if found:
                    return found
            elif isinstance(nested, list):
                for item in nested:
                    found = LlamaGenVideoAdapter._extract_media_url(item)
                    if found:
                        return found
        return None

    @staticmethod
    def _extract_error(data: object) -> str:
        if not isinstance(data, dict):
            return "LlamaGen generation failed"
        for key in ("error", "message", "error_message"):
            value = data.get(key)
            if value:
                return str(value)[:500]
        nested = data.get("data")
        if isinstance(nested, dict):
            return LlamaGenVideoAdapter._extract_error(nested)
        return "LlamaGen generation failed"

    def cancel(self, provider_run_id: str) -> bool:
        # The documented generation endpoints used here expose create/status;
        # no cancellation endpoint is assumed.
        return False
