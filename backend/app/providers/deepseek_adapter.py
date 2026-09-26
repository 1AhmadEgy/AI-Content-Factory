from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class DeepSeekModelAdapter(ModelAdapter):
    """DeepSeek Chat Completions adapter using the current OpenAI-compatible API."""

    def __init__(self, model_id: str, api_key: str | None = None) -> None:
        self.model_id = model_id
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")

    def capability(self) -> ModelCapability:
        return ModelCapability(
            category="generation",
            capabilities=frozenset({"generation", "text", "story", "script", "scene", "shot", "character", "world", "reasoning", "real-provider"}),
            runtime="CLOUD",
            license_status="CONFIGURED",
        )

    def health_check(self) -> bool:
        return bool(self.api_key)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(False, error_code="DEEPSEEK_API_KEY_MISSING", error_message="DEEPSEEK_API_KEY is not configured")
        messages = request.parameters.get("messages")
        if not isinstance(messages, list) or not messages:
            prompt = str(request.parameters.get("prompt", "")).strip()
            if not prompt:
                return ProviderResponse(False, error_code="PROMPT_REQUIRED", error_message="prompt is required")
            messages = [{"role": "user", "content": prompt}]

        payload: dict[str, Any] = {"model": request.model, "messages": messages}
        for key in ("temperature", "top_p", "max_tokens", "stop", "tools", "tool_choice"):
            if key in request.parameters:
                payload[key] = request.parameters[key]
        if request.parameters.get("response_format") == "json":
            payload["response_format"] = {"type": "json_object"}
        if request.parameters.get("thinking") is not None:
            payload["thinking"] = request.parameters["thinking"]
        if request.parameters.get("reasoning_effort") is not None:
            payload["reasoning_effort"] = request.parameters["reasoning_effort"]

        endpoint = "https://api.deepseek.com/chat/completions"
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=float(os.getenv("AICF_PROVIDER_TIMEOUT_SECONDS", "120"))) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return ProviderResponse(False, error_code="DEEPSEEK_REQUEST_FAILED", error_message=f"HTTP {exc.code}: {detail[:1000]}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return ProviderResponse(False, error_code="DEEPSEEK_REQUEST_FAILED", error_message=str(exc))

        choices = data.get("choices") or []
        message = choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
        output = str(message.get("content") or "").strip()
        if not output:
            return ProviderResponse(False, error_code="DEEPSEEK_EMPTY_TEXT", error_message="DeepSeek returned no text")
        usage = data.get("usage") or {}
        metrics = {}
        if isinstance(usage, dict):
            if isinstance(usage.get("prompt_tokens"), (int, float)):
                metrics["input_tokens"] = float(usage["prompt_tokens"])
            if isinstance(usage.get("completion_tokens"), (int, float)):
                metrics["output_tokens"] = float(usage["completion_tokens"])
        return ProviderResponse(True, output_text=output, provider_run_id=str(data.get("id") or uuid.uuid4()), metrics=metrics)

    def cancel(self, provider_run_id: str) -> bool:
        return False
