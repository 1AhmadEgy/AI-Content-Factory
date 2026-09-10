from __future__ import annotations

import hashlib
import json
import uuid
from urllib.error import URLError
from urllib.request import Request, urlopen

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class MockModelAdapter(ModelAdapter):
    """Zero-cost adapter for deterministic end-to-end pipeline tests."""

    def __init__(self, model_id: str = "mock-deterministic") -> None:
        self.model_id = model_id

    def capability(self) -> ModelCapability:
        return ModelCapability(
            category="generation",
            capabilities=frozenset({"story", "script", "scene", "shot", "image", "video", "tts", "music", "sfx", "qc", "render"}),
            runtime="MOCK",
            license_status="OPEN",
        )

    def health_check(self) -> bool:
        return True

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        material = f"{self.model_id}|{request.model}|{request.seed}|{sorted(request.parameters.items())}"
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return ProviderResponse(
            success=True,
            output_text=request.parameters.get("mock_text"),
            provider_run_id=f"mock-{uuid.uuid5(uuid.NAMESPACE_URL, digest)}",
            metrics={"deterministic": 1.0},
        )

    def cancel(self, provider_run_id: str) -> bool:
        return provider_run_id.startswith("mock-")


class LocalModelAdapter(ModelAdapter):
    """OpenAI-compatible local HTTP adapter; works with local LLM servers."""

    def __init__(self, endpoint: str, capabilities: frozenset[str] | None = None, timeout_seconds: int = 120) -> None:
        self.endpoint = endpoint.rstrip("/")
        self._capabilities = capabilities or frozenset()
        self.timeout_seconds = timeout_seconds

    def capability(self) -> ModelCapability:
        return ModelCapability(category="generation", capabilities=self._capabilities, runtime="LOCAL", license_status="OPEN")

    def health_check(self) -> bool:
        return bool(self.endpoint)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        payload = {
            "model": request.model,
            "messages": request.parameters.get("messages", [{"role": "user", "content": request.parameters.get("prompt", "")}]),
            "temperature": request.parameters.get("temperature", 0.7),
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        try:
            req = Request(self.endpoint + "/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data["choices"][0]["message"]["content"]
            return ProviderResponse(success=True, output_text=text, provider_run_id=str(data.get("id") or "local"))
        except (KeyError, IndexError, json.JSONDecodeError, OSError, URLError) as exc:
            return ProviderResponse(success=False, error_code="LOCAL_PROVIDER_ERROR", error_message=str(exc))

    def cancel(self, provider_run_id: str) -> bool:
        return False


class CloudModelAdapter(ModelAdapter):
    """Provider-neutral cloud contract; concrete SDKs belong outside the core."""

    def __init__(self, provider_name: str, capabilities: frozenset[str] | None = None) -> None:
        self.provider_name = provider_name
        self._capabilities = capabilities or frozenset()

    def capability(self) -> ModelCapability:
        return ModelCapability(category="generation", capabilities=self._capabilities, runtime="CLOUD")

    def health_check(self) -> bool:
        return bool(self.provider_name)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError("Cloud transport must be implemented by the selected provider adapter")

    def cancel(self, provider_run_id: str) -> bool:
        return False
