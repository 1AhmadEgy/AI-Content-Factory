from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class HuggingFaceMediaAdapter(ModelAdapter):
    """Real Hugging Face Inference Providers task endpoint for binary media."""

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
        parameters = {k: v for k, v in request.parameters.items() if k not in {"prompt", "character_ids", "location_ids", "country_id", "library_id", "continuity_rules", "production_context"}}
        if request.seed is not None:
            parameters["seed"] = request.seed
        if parameters:
            payload["parameters"] = parameters
        url = f"https://router.huggingface.co/hf-inference/models/{self.model}"
        try:
            req = Request(url, data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read()
                mime = response.headers.get("Content-Type", "application/octet-stream").split(";", 1)[0]
                run_id = response.headers.get("x-request-id") or response.headers.get("x-amzn-requestid")
            if not body:
                return ProviderResponse(False, error_code="HF_EMPTY_OUTPUT", error_message="Provider returned empty output")
            if mime == "application/json":
                data = json.loads(body.decode())
                message = data.get("error") if isinstance(data, dict) else None
                return ProviderResponse(False, provider_run_id=run_id, error_code="HF_PROVIDER_ERROR", error_message=str(message or "Provider returned JSON instead of binary media"))
            if not run_id:
                return ProviderResponse(False, error_code="HF_RUN_ID_MISSING", error_message="Provider did not return a request id")
            return ProviderResponse(True, output_bytes=body, output_mime_type=mime, provider_run_id=run_id, output_metadata={"task": self.task})
        except HTTPError as exc:
            return ProviderResponse(False, error_code="HF_HTTP_ERROR", error_message=f"HTTP {exc.code}: {exc.reason}")
        except (URLError, OSError, ValueError, json.JSONDecodeError) as exc:
            return ProviderResponse(False, error_code="HF_PROVIDER_ERROR", error_message=str(exc))

    def cancel(self, provider_run_id: str) -> bool:
        return False
