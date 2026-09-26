from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class AnthropicProviderError(RuntimeError):
    pass


class AnthropicModelAdapter(ModelAdapter):
    """Anthropic Messages API adapter for text generation."""

    def __init__(self, model_id: str, api_key: str | None = None) -> None:
        self.model_id = model_id
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    def capability(self) -> ModelCapability:
        return ModelCapability(
            category="generation",
            capabilities=frozenset({"generation", "text", "story", "script", "scene", "shot", "character", "world", "real-provider"}),
            runtime="CLOUD",
            license_status="CONFIGURED",
        )

    def health_check(self) -> bool:
        return bool(self.api_key)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(False, error_code="ANTHROPIC_API_KEY_MISSING", error_message="ANTHROPIC_API_KEY is not configured")
        prompt = str(request.parameters.get("prompt", "")).strip()
        messages = request.parameters.get("messages")
        if not prompt and isinstance(messages, list):
            messages = [m for m in messages if isinstance(m, dict) and m.get("role") in {"user", "assistant"}]
        else:
            messages = [{"role": "user", "content": prompt}]
        if not messages:
            return ProviderResponse(False, error_code="PROMPT_REQUIRED", error_message="prompt is required")

        payload: dict[str, Any] = {
            "model": request.model,
            "max_tokens": int(request.parameters.get("max_tokens", 4096)),
            "messages": messages,
        }
        if request.parameters.get("system"):
            payload["system"] = str(request.parameters["system"])
        # Current Claude APIs deprecate non-default temperature/top_p/top_k on newer models.
        # Only forward them when explicitly requested and leave model defaults otherwise.
        for key in ("temperature", "top_p", "top_k"):
            if key in request.parameters:
                payload[key] = request.parameters[key]

        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=float(os.getenv("AICF_PROVIDER_TIMEOUT_SECONDS", "120"))) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return ProviderResponse(False, error_code="ANTHROPIC_REQUEST_FAILED", error_message=f"HTTP {exc.code}: {detail[:1000]}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return ProviderResponse(False, error_code="ANTHROPIC_REQUEST_FAILED", error_message=str(exc))

        parts = []
        for block in data.get("content", []) or []:
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
                parts.append(block["text"])
        output = "\n".join(parts).strip()
        if not output:
            return ProviderResponse(False, error_code="ANTHROPIC_EMPTY_TEXT", error_message="Anthropic returned no text")
        usage = data.get("usage") or {}
        metrics = {}
        if isinstance(usage, dict):
            if isinstance(usage.get("input_tokens"), (int, float)):
                metrics["input_tokens"] = float(usage["input_tokens"])
            if isinstance(usage.get("output_tokens"), (int, float)):
                metrics["output_tokens"] = float(usage["output_tokens"])
        return ProviderResponse(True, output_text=output, provider_run_id=str(data.get("id") or uuid.uuid4()), metrics=metrics)

    def cancel(self, provider_run_id: str) -> bool:
        return False
