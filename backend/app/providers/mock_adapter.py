from __future__ import annotations

import hashlib

from .contracts import ModelAdapter, ModelCapability, ProviderRequest, ProviderResponse


class MockModelAdapter(ModelAdapter):
    def __init__(self, model_id: str = "mock-v1", category: str = "IMAGE") -> None:
        self.model_id = model_id
        self.category = category

    def capability(self) -> ModelCapability:
        return ModelCapability(
            category=self.category,
            capabilities=frozenset({"deterministic", "offline"}),
            runtime="CUSTOM",
            license_status="VERIFIED",
        )

    def health_check(self) -> bool:
        return True

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        material = f"{self.model_id}|{request.model}|{request.seed}|{sorted(request.parameters.items())}"
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return ProviderResponse(
            success=True,
            output_asset_ids=[f"provider-mock-{digest[:24]}"],
            provider_run_id=f"provider-run-{digest[:16]}",
            metrics={"deterministic": 1.0},
        )

    def cancel(self, provider_run_id: str) -> bool:
        return True
