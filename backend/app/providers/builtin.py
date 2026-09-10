from __future__ import annotations

import hashlib
import uuid

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class MockModelAdapter(ModelAdapter):
    """Zero-cost adapter for deterministic end-to-end pipeline tests."""

    def __init__(self, model_id: str = "mock-deterministic") -> None:
        self.model_id = model_id

    def capability(self) -> ModelCapability:
        return ModelCapability(
            category="generation",
            capabilities=frozenset({"story", "image", "video", "tts", "music", "sfx", "qc", "render"}),
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
            provider_run_id=f"mock-{uuid.uuid5(uuid.NAMESPACE_URL, digest)}",
            metrics={"deterministic": 1.0},
        )

    def cancel(self, provider_run_id: str) -> bool:
        return provider_run_id.startswith("mock-")


class LocalModelAdapter(ModelAdapter):
    """Contract-preserving adapter for a locally hosted model endpoint."""

    def __init__(self, endpoint: str, capabilities: frozenset[str] | None = None) -> None:
        self.endpoint = endpoint.rstrip("/")
        self._capabilities = capabilities or frozenset()

    def capability(self) -> ModelCapability:
        return ModelCapability(category="generation", capabilities=self._capabilities, runtime="LOCAL")

    def health_check(self) -> bool:
        return bool(self.endpoint)

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        raise NotImplementedError("Local transport must be implemented by the selected runtime adapter")

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
