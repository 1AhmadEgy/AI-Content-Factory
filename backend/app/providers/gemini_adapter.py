from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Any

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class GeminiProviderError(RuntimeError):
    pass


class GeminiModelAdapter(ModelAdapter):
    """Google Gemini REST adapter for text generation."""

    def __init__(self, model_id: str, api_key: str | None = None) -> None:
        self.model_id = model_id
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")

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
            return ProviderResponse(False, error_code="GEMINI_API_KEY_MISSING", error_message="GEMINI_API_KEY is not configured")
        prompt = str(request.parameters.get("prompt", "")).strip()
        if not prompt:
            messages = request.parameters.get("messages") or []
            prompt = "\n".join(str(m.get("content", "")) for m in messages if isinstance(m, dict)).strip()
        if not prompt:
            return ProviderResponse(False, error_code="PROMPT_REQUIRED", error_message="prompt is required")

        contents = [{"role": "user", "parts": [{"text": prompt}]}]
        payload: dict[str, Any] = {"contents": contents}
        generation_config: dict[str, Any] = {}
        for source, target in (("temperature", "temperature"), ("top_p", "topP"), ("max_tokens", "maxOutputTokens")):
            if source in request.parameters:
                generation_config[target] = request.parameters[source]
        if request.parameters.get("response_format") == "json":
            generation_config["responseMimeType"] = "application/json"
        if generation_config:
            payload["generationConfig"] = generation_config

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{request.model}:generateContent"
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=float(os.getenv("AICF_PROVIDER_TIMEOUT_SECONDS", "120"))) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return ProviderResponse(False, error_code="GEMINI_REQUEST_FAILED", error_message=f"HTTP {exc.code}: {detail[:1000]}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return ProviderResponse(False, error_code="GEMINI_REQUEST_FAILED", error_message=str(exc))

        parts: list[str] = []
        for candidate in data.get("candidates", []) or []:
            content = candidate.get("content", {}) if isinstance(candidate, dict) else {}
            for part in content.get("parts", []) or []:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    parts.append(part["text"])
        output = "\n".join(parts).strip()
        if not output:
            return ProviderResponse(False, error_code="GEMINI_EMPTY_TEXT", error_message="Gemini returned no text")
        usage = data.get("usageMetadata") or {}
        metrics = {}
        if isinstance(usage, dict):
            if isinstance(usage.get("promptTokenCount"), (int, float)):
                metrics["input_tokens"] = float(usage["promptTokenCount"])
            if isinstance(usage.get("candidatesTokenCount"), (int, float)):
                metrics["output_tokens"] = float(usage["candidatesTokenCount"])
        return ProviderResponse(True, output_text=output, provider_run_id=str(data.get("responseId") or uuid.uuid4()), metrics=metrics)

    def cancel(self, provider_run_id: str) -> bool:
        return False
