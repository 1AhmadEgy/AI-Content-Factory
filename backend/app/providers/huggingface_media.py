from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class HuggingFaceMediaAdapter(ModelAdapter):
    """Real Hugging Face Inference Providers task endpoint for binary media.

    The adapter intentionally uses the task payload documented by Hugging Face
    (`inputs` plus optional `parameters`) and never fabricates a provider run id.
    Synchronous routed inference can legitimately return media without exposing
    a request id to the caller, so provider_run_id is optional at this layer.
    """

    _CONTINUITY_KEYS = frozenset({
        "prompt",
        "character_ids",
        "location_ids",
        "country_id",
        "library_id",
        "continuity_rules",
        "production_context",
    })

    def __init__(self, token: str, model: str, task: str, capabilities: frozenset[str], timeout_seconds: int = 300) -> None:
        self.token = token
        self.model = model
        self.task = task
        self._capabilities = capabilities
        self.timeout_seconds = timeout_seconds

    def capability(self) -> ModelCapability:
        return ModelCapability(category="generation", capabilities=self._capabilities, runtime="CLOUD")

    def health_check(self) -> bool:
        return bool(self.token and self.model and self.task)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        prompt = request.parameters.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            return ProviderResponse(False, error_code="HF_EMPTY_PROMPT", error_message="Media generation requires a non-empty prompt")

        payload: dict[str, object] = {"inputs": prompt}
        parameters = {
            key: value
            for key, value in request.parameters.items()
            if key not in self._CONTINUITY_KEYS
        }
        if request.seed is not None and "seed" not in parameters:
            parameters["seed"] = request.seed
        if parameters:
            payload["parameters"] = parameters

        url = f"https://router.huggingface.co/hf-inference/models/{self.model}"
        try:
            req = Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read()
                mime = response.headers.get("Content-Type", "application/octet-stream").split(";", 1)[0].lower()
                # Preserve a real provider/request id when the upstream exposes one.
                # Never manufacture one locally when the synchronous response omits it.
                run_id = (
                    response.headers.get("Inference-Id")
                    or response.headers.get("inference-id")
                    or response.headers.get("x-request-id")
                    or response.headers.get("x-amzn-requestid")
                )

            if not body:
                return ProviderResponse(False, error_code="HF_EMPTY_OUTPUT", error_message="Provider returned empty output")

            if mime == "application/json" or mime.endswith("+json"):
                try:
                    data = json.loads(body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return ProviderResponse(False, error_code="HF_PROVIDER_ERROR", error_message="Provider returned invalid JSON")
                message = data.get("error") if isinstance(data, dict) else None
                return ProviderResponse(
                    False,
                    provider_run_id=run_id,
                    error_code="HF_PROVIDER_ERROR",
                    error_message=str(message or "Provider returned JSON instead of binary media"),
                )

            return ProviderResponse(
                True,
                output_bytes=body,
                output_mime_type=mime,
                provider_run_id=run_id,
                output_metadata={"task": self.task, "model": self.model},
            )
        except HTTPError as exc:
            return ProviderResponse(False, error_code="HF_HTTP_ERROR", error_message=f"HTTP {exc.code}: {exc.reason}")
        except (URLError, OSError, ValueError) as exc:
            return ProviderResponse(False, error_code="HF_PROVIDER_ERROR", error_message=str(exc))

    def cancel(self, provider_run_id: str) -> bool:
        return False
