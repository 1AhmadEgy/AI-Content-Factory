import pytest

from app.providers.provider_layer import (
    ProviderCapability,
    ProviderRegistry,
    ProviderResult,
    ProviderScoreWeights,
    ProviderSpec,
    ProviderUnavailableError,
)


class FakeProvider:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls = 0

    def execute(self, payload: object) -> ProviderResult:
        self.calls += 1
        return ProviderResult(success=True, output={"provider": self.name, "payload": payload})


def test_resolution_is_lazy_and_selects_best_available_provider() -> None:
    created: list[str] = []

    def make(name: str):
        def factory() -> FakeProvider:
            created.append(name)
            return FakeProvider(name)

        return factory

    registry = ProviderRegistry()
    registry.register(
        ProviderSpec(
            "slow",
            frozenset({ProviderCapability.TEXT}),
            make("slow"),
            quality=0.9,
            reliability=0.9,
            latency=0.2,
        )
    )
    registry.register(
        ProviderSpec(
            "fast",
            frozenset({ProviderCapability.TEXT}),
            make("fast"),
            quality=0.8,
            reliability=0.8,
            latency=0.9,
        )
    )

    assert created == []
    resolved = registry.resolve(
        ProviderCapability.TEXT,
        weights=ProviderScoreWeights(quality=1, reliability=1, latency=3),
    )
    assert resolved.spec.id == "fast"
    assert created == ["fast"]


def test_explicit_provider_never_silently_falls_back() -> None:
    registry = ProviderRegistry()
    registry.register(
        ProviderSpec("image", frozenset({ProviderCapability.IMAGE}), lambda: FakeProvider("image"))
    )
    registry.register(
        ProviderSpec("text", frozenset({ProviderCapability.TEXT}), lambda: FakeProvider("text"))
    )

    with pytest.raises(ProviderUnavailableError, match="no silent fallback"):
        registry.resolve(ProviderCapability.VIDEO, provider_id="image")


def test_circuit_breaker_opens_after_failures() -> None:
    class FailingProvider:
        def execute(self, payload: object) -> ProviderResult:
            return ProviderResult(success=False, error_message="upstream unavailable")

    registry = ProviderRegistry(circuit_failure_threshold=2, circuit_cooldown_seconds=60)
    registry.register(
        ProviderSpec("video", frozenset({ProviderCapability.VIDEO}), lambda: FailingProvider())
    )

    registry.execute(ProviderCapability.VIDEO, {})
    registry.execute(ProviderCapability.VIDEO, {})
    health = registry.health("video")
    assert health.consecutive_failures == 2
    assert health.opened_at is not None

    with pytest.raises(ProviderUnavailableError, match="currently unavailable"):
        registry.resolve(ProviderCapability.VIDEO, provider_id="video")


def test_execute_attaches_provenance_and_provider_id() -> None:
    registry = ProviderRegistry()
    registry.register(
        ProviderSpec("text", frozenset({ProviderCapability.TEXT}), lambda: FakeProvider("text"))
    )

    result = registry.execute(ProviderCapability.TEXT, {"prompt": "hello"})
    assert result.success
    assert result.provider_id == "text"
    assert result.provenance["provider_id"] == "text"
    assert "provider_score" in result.provenance
