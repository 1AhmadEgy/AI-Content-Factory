from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class LocalModelAdapter(ModelAdapter):
    """OpenAI-compatible local HTTP adapter for Ollama, LM Studio and similar servers."""

    def __init__(self, endpoint: str, capabilities: frozenset[str] | None = None, timeout_seconds: int = 120) -> None:
        self.endpoint = endpoint.rstrip("/")
        self._capabilities = capabilities or frozenset()
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
            return ProviderResponse(success=True, output_text=text, provider_run_id=str(data.get("id") or "local"), metrics={"local": 1.0})
        except (KeyError, IndexError, json.JSONDecodeError, OSError, URLError) as exc:
            return ProviderResponse(success=False, error_code="LOCAL_PROVIDER_ERROR", error_message=str(exc))

    def cancel(self, provider_run_id: str) -> bool:
        return False
