from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class ComfyUIModelAdapter(ModelAdapter):
    """Generic ComfyUI API adapter for reusable workflows.

    The workflow is supplied by the job as parameters["workflow"] or by
    AICF_COMFYUI_WORKFLOW_JSON. The adapter does not embed a model-specific
    graph in the domain layer.
    """

    _CAPABILITIES = frozenset({"image", "video", "generation", "comfyui", "media"})

    def __init__(
        self,
        model_id: str,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int = 600,
        poll_interval_seconds: float = 2.0,
        capabilities: frozenset[str] | None = None,
    ) -> None:
        self.model_id = model_id
        self.base_url = (base_url or os.getenv("AICF_COMFYUI_BASE_URL", "http://127.0.0.1:8188")).rstrip("/")
        self.api_key = api_key or os.getenv("AICF_COMFYUI_API_KEY", "")
        self.timeout_seconds = max(1, timeout_seconds)
        self.poll_interval_seconds = max(0.2, poll_interval_seconds)
        self._capabilities = (capabilities or self._CAPABILITIES) & self._CAPABILITIES

    def capability(self) -> ModelCapability:
        return ModelCapability(
            category="generation",
            capabilities=self._capabilities,
            runtime="LOCAL",
            license_status="CONFIGURED",
        )

    def health_check(self) -> bool:
        parsed = urllib.parse.urlparse(self.base_url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        workflow = request.parameters.get("workflow")
        if workflow is None:
            raw = os.getenv("AICF_COMFYUI_WORKFLOW_JSON", "").strip()
            if raw:
                try:
                    workflow = json.loads(raw)
                except json.JSONDecodeError as exc:
                    return ProviderResponse(False, error_code="COMFYUI_WORKFLOW_INVALID", error_message=str(exc))
        if not isinstance(workflow, dict) or not workflow:
            return ProviderResponse(False, error_code="COMFYUI_WORKFLOW_REQUIRED", error_message="A ComfyUI workflow graph is required")

        workflow = json.loads(json.dumps(workflow))
        inputs = request.parameters.get("prompt_inputs") or {}
        if not isinstance(inputs, dict):
            return ProviderResponse(False, error_code="COMFYUI_PROMPT_INPUTS_INVALID")

        for key, value in inputs.items():
            if not isinstance(key, str) or "." not in key:
                return ProviderResponse(False, error_code="COMFYUI_PROMPT_INPUT_KEY_INVALID", error_message=str(key))
            node_id, input_name = key.split(".", 1)
            node = workflow.get(node_id)
            if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
                return ProviderResponse(False, error_code="COMFYUI_NODE_NOT_FOUND", error_message=node_id)
            node["inputs"][input_name] = value

        payload: dict[str, Any] = {"prompt": workflow, "client_id": str(uuid.uuid4())}
        if request.seed is not None:
            payload["extra_data"] = {"aicf_seed": request.seed}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            created = self._request_json("POST", "/prompt", payload, headers)
            prompt_id = self._prompt_id(created)
            if not prompt_id:
                return ProviderResponse(False, error_code="COMFYUI_INVALID_PROMPT_RESPONSE")

            deadline = time.monotonic() + self.timeout_seconds
            while time.monotonic() < deadline:
                history = self._request_json("GET", f"/history/{urllib.parse.quote(prompt_id, safe='')}", None, headers)
                entry = history.get(prompt_id) if isinstance(history, dict) else None
                if isinstance(entry, dict):
                    status = entry.get("status") or {}
                    status_str = str(status.get("status_str", "")).lower() if isinstance(status, dict) else ""
                    if status_str in {"error", "failed"}:
                        messages = status.get("messages", []) if isinstance(status, dict) else []
                        return ProviderResponse(False, provider_run_id=prompt_id, error_code="COMFYUI_EXECUTION_FAILED", error_message=str(messages)[:1000])
                    outputs = entry.get("outputs")
                    if isinstance(outputs, dict):
                        media = self._collect_outputs(outputs, headers)
                        if media:
                            body, mime, filename, metadata = media
                            return ProviderResponse(True, output_bytes=body, output_mime_type=mime, output_filename=filename, output_metadata={"prompt_id": prompt_id, **metadata}, provider_run_id=prompt_id)
                time.sleep(self.poll_interval_seconds)

            return ProviderResponse(False, provider_run_id=prompt_id, error_code="COMFYUI_TIMEOUT", error_message="Workflow did not produce a usable output before timeout")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return ProviderResponse(False, error_code="COMFYUI_HTTP_ERROR", error_message=f"HTTP {exc.code}: {detail[:1000]}")
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError, TypeError) as exc:
            return ProviderResponse(False, error_code="COMFYUI_PROVIDER_ERROR", error_message=str(exc)[:1000])

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None, headers: dict[str, str]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(self.base_url + path, data=body, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=min(self.timeout_seconds, 60)) as response:
            decoded = json.loads(response.read().decode("utf-8"))
        if not isinstance(decoded, dict):
            raise ValueError("ComfyUI returned a non-object JSON response")
        return decoded

    def _collect_outputs(self, outputs: dict[str, Any], headers: dict[str, str]) -> tuple[bytes, str, str, dict[str, Any]] | None:
        for node_id, node_output in outputs.items():
            if not isinstance(node_output, dict):
                continue
            for field in ("images", "gifs", "videos", "audio"):
                items = node_output.get(field)
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    filename = str(item.get("filename", "")).strip()
                    if not filename:
                        continue
                    query = urllib.parse.urlencode({"filename": filename, "subfolder": str(item.get("subfolder", "")), "type": str(item.get("type", "output"))})
                    request = urllib.request.Request(self.base_url + "/view?" + query, headers=headers, method="GET")
                    with urllib.request.urlopen(request, timeout=60) as response:
                        body = response.read()
                        mime = response.headers.get_content_type() or self._mime_for_field(field)
                    if body:
                        return body, mime, filename, {"node_id": node_id, "output_type": field}
        return None

    @staticmethod
    def _prompt_id(data: dict[str, Any]) -> str | None:
        for key in ("prompt_id", "id"):
            value = data.get(key)
            if value:
                return str(value)
        return None

    @staticmethod
    def _mime_for_field(field: str) -> str:
        return {"images": "image/png", "gifs": "image/gif", "videos": "video/mp4", "audio": "audio/mpeg"}.get(field, "application/octet-stream")

    def cancel(self, provider_run_id: str) -> bool:
        return False
