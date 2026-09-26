from __future__ import annotations

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class RunwayVideoAdapter(ModelAdapter):
    """Runway Dev video adapter using the asynchronous task API.

    The adapter submits a video task, polls its task id, downloads the ephemeral
    output URL, and returns durable bytes to the existing asset/provenance layer.
    """

    _CAPABILITIES = frozenset(
        {"video", "text-to-video", "image-to-video", "generation", "media"}
    )
    _BASE_URL = "https://api.dev.runwayml.com/v1"
    _API_VERSION = "2024-11-06"

    def __init__(
        self,
        model_id: str = "gen4.5",
        api_key: str | None = None,
        timeout_seconds: int = 600,
        poll_interval_seconds: int = 3,
    ) -> None:
        self.model_id = model_id.strip() or "gen4.5"
        self.api_key = api_key or os.getenv("RUNWAYML_API_SECRET", "")
        self.timeout_seconds = max(30, timeout_seconds)
        self.poll_interval_seconds = max(1, poll_interval_seconds)

    def capability(self) -> ModelCapability:
        return ModelCapability(
            category="generation",
            capabilities=self._CAPABILITIES,
            runtime="CLOUD",
            license_status="CONFIGURED",
        )

    def health_check(self) -> bool:
        return bool(self.api_key)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(False, error_code="RUNWAY_API_KEY_MISSING")

        parameters = dict(request.parameters)
        prompt = parameters.pop("prompt", parameters.pop("promptText", ""))
        if not isinstance(prompt, str) or not prompt.strip():
            return ProviderResponse(False, error_code="RUNWAY_PROMPT_REQUIRED")

        model = str(parameters.pop("model", "") or request.model or self.model_id)
        payload: dict[str, object] = {
            "model": model,
            "promptText": prompt,
            "ratio": self._ratio(parameters.pop("ratio", parameters.pop("aspect_ratio", "1280:768"))),
            "duration": int(parameters.pop("duration", 5)),
        }

        prompt_image = parameters.pop("promptImage", parameters.pop("prompt_image", None))
        if prompt_image:
            if not self._valid_input_reference(prompt_image):
                return ProviderResponse(
                    False,
                    error_code="RUNWAY_INVALID_INPUT_REFERENCE",
                    error_message="promptImage must be an HTTPS URL or data URI",
                )
            payload["promptImage"] = prompt_image

        # Preserve supported provider-specific parameters without forcing them
        # into the shared domain contract.
        for key in ("seed", "contentModeration", "content_moderation"):
            if key in parameters:
                payload[key] = parameters[key]
        if request.seed is not None:
            payload["seed"] = request.seed

        try:
            task = self._request_json("POST", "/image_to_video", payload)
            task_id = self._task_id(task)
            if not task_id:
                return ProviderResponse(
                    False,
                    error_code="RUNWAY_INVALID_CREATE_RESPONSE",
                    error_message="Runway response did not contain a task id",
                )

            result = self._wait_for_task(task_id)
            status = str(result.get("status", "")).upper()

            if status != "SUCCEEDED":
                return ProviderResponse(
                    False,
                    provider_run_id=task_id,
                    error_code="RUNWAY_TASK_FAILED",
                    error_message=self._task_error(result),
                    output_metadata={"status": status},
                )

            output_url = self._output_url(result)
            if not output_url:
                return ProviderResponse(
                    False,
                    provider_run_id=task_id,
                    error_code="RUNWAY_OUTPUT_MISSING",
                    error_message="Runway task succeeded without an output URL",
                )

            media, mime = self._download_output(output_url)
            return ProviderResponse(
                True,
                output_bytes=media,
                output_mime_type=mime or "video/mp4",
                output_filename=f"runway-{task_id}.mp4",
                output_metadata={
                    "provider": "runway",
                    "model": model,
                    "taskStatus": status,
                },
                provider_run_id=task_id,
            )
        except HTTPError as exc:
            return ProviderResponse(
                False,
                error_code="RUNWAY_HTTP_ERROR",
                error_message=f"HTTP {exc.code}: {exc.reason}",
            )
        except (OSError, URLError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return ProviderResponse(
                False,
                error_code="RUNWAY_PROVIDER_ERROR",
                error_message=str(exc)[:500],
            )

    def cancel(self, provider_run_id: str) -> bool:
        if not self.api_key or not provider_run_id:
            return False
        try:
            self._request_json("DELETE", f"/tasks/{provider_run_id}", None)
            return True
        except (HTTPError, OSError, URLError, ValueError, TypeError, json.JSONDecodeError):
            return False

    def _request_json(self, method: str, path: str, payload: dict[str, object] | None) -> dict:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            self._BASE_URL + path,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Runway-Version": self._API_VERSION,
            },
            method=method,
        )
        with urlopen(request, timeout=min(self.timeout_seconds, 60)) as response:
            value = json.loads(response.read().decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Runway returned a non-object JSON response")
        return value

    def _wait_for_task(self, task_id: str) -> dict:
        deadline = time.monotonic() + self.timeout_seconds
        last: dict = {"id": task_id, "status": "PENDING"}
        while time.monotonic() < deadline:
            last = self._request_json("GET", f"/tasks/{task_id}", None)
            status = str(last.get("status", "")).upper()
            if status in {"SUCCEEDED", "FAILED", "CANCELED", "CANCELLED"}:
                return last
            time.sleep(self.poll_interval_seconds)
        raise TimeoutError(f"Runway task timed out: {task_id}")

    @staticmethod
    def _task_id(data: dict) -> str | None:
        value = data.get("id")
        return str(value) if value else None

    @staticmethod
    def _output_url(data: dict) -> str | None:
        output = data.get("output")
        if isinstance(output, list):
            for item in output:
                if isinstance(item, str) and item.startswith("https://"):
                    return item
        if isinstance(output, str) and output.startswith("https://"):
            return output
        return None

    @staticmethod
    def _task_error(data: dict) -> str:
        details = data.get("failure") or data.get("error") or data.get("failureCode")
        if isinstance(details, dict):
            return str(details.get("message") or details)
        return str(details or "Runway task failed")

    @staticmethod
    def _ratio(value: object) -> str:
        ratio = str(value)
        if ratio in {"16:9", "1280:720"}:
            return "1280:768"
        if ratio in {"9:16", "720:1280"}:
            return "768:1280"
        if ratio not in {"1280:768", "768:1280"}:
            raise ValueError(f"Unsupported Runway video ratio: {ratio}")
        return ratio

    @staticmethod
    def _valid_input_reference(value: object) -> bool:
        if not isinstance(value, str):
            return False
        return value.startswith("data:image/") or value.startswith("https://")

    @staticmethod
    def _download_output(url: str) -> tuple[bytes, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Runway output URL must be HTTPS")
        request = Request(url, headers={"Accept": "video/*,application/octet-stream"}, method="GET")
        with urlopen(request, timeout=120) as response:
            content_type = response.headers.get("Content-Type", "video/mp4").split(";", 1)[0].strip()
            data = response.read()
        if not data:
            raise ValueError("Runway returned an empty video")
        return data, content_type
