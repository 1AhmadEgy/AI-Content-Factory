from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from time import monotonic
from typing import Any, Callable, Protocol


class ProviderCapability(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"
    TTS = "tts"
    MUSIC = "music"
    SFX = "sfx"
    LIPSYNC = "lipsync"
    TRANSCRIBE = "transcribe"
    RENDER = "render"
    QC = "qc"


@dataclass(frozen=True, slots=True)
class ProviderResult:
    success: bool
    output: Any = None
    provider_id: str | None = None
    provider_run_id: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


class ProviderContract(Protocol):
    def execute(self, payload: Any) -> ProviderResult: ...


ProviderFactory = Callable[[], ProviderContract]


class ProviderUnavailableError(RuntimeError):
    def __init__(self, message: str, *, capability: ProviderCapability | None = None, provider_id: str | None = None) -> None:
        super().__init__(message)
        self.capability = capability
        self.provider_id = provider_id


@dataclass(slots=True)
class ProviderHealth:
    available: bool = True
    consecutive_failures: int = 0
    last_error: str | None = None
    opened_at: float | None = None

    def circuit_open(self, cooldown_seconds: float) -> bool:
        if self.opened_at is None:
            return False
        if monotonic() - self.opened_at >= cooldown_seconds:
            self.opened_at = None
            self.consecutive_failures = 0
            return False
        return True


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    id: str
    capabilities: frozenset[ProviderCapability]
    factory: ProviderFactory
    priority: float = 0.0
    task_fit: float = 1.0
    quality: float = 0.5
    reliability: float = 0.5
    cost_efficiency: float = 0.5
    latency: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)

    def supports(self, capability: ProviderCapability) -> bool:
        return capability in self.capabilities


@dataclass(frozen=True, slots=True)
class ProviderScore:
    provider_id: str
    total: float
    dimensions: dict[str, float]


@dataclass(frozen=True, slots=True)
class ResolvedProvider:
    spec: ProviderSpec
    provider: ProviderContract
    score: ProviderScore


@dataclass(frozen=True, slots=True)
class ProviderScoreWeights:
    task_fit: float = 1.0
    quality: float = 1.0
    reliability: float = 1.0
    cost_efficiency: float = 1.0
    latency: float = 1.0
    priority: float = 1.0
    availability: float = 1.0


class ProviderRegistry:
    """Contract-first provider registry with explicit routing and lazy adapters."""

    def __init__(self, *, circuit_failure_threshold: int = 3, circuit_cooldown_seconds: float = 30.0) -> None:
        if circuit_failure_threshold < 1:
            raise ValueError("circuit_failure_threshold must be >= 1")
        self._specs: dict[str, ProviderSpec] = {}
        self._instances: dict[str, ProviderContract] = {}
        self._health: dict[str, ProviderHealth] = {}
        self._lock = Lock()
        self._failure_threshold = circuit_failure_threshold
        self._cooldown_seconds = circuit_cooldown_seconds

    def register(self, spec: ProviderSpec) -> None:
        if not spec.id.strip():
            raise ValueError("provider id must not be empty")
        if not spec.capabilities:
            raise ValueError(f"provider {spec.id!r} must declare at least one capability")
        with self._lock:
            if spec.id in self._specs:
                raise ValueError(f"Provider already registered: {spec.id}")
            self._specs[spec.id] = spec
            self._health[spec.id] = ProviderHealth()

    def get(self, provider_id: str) -> ProviderSpec | None:
        return self._specs.get(provider_id)

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._specs))

    def health(self, provider_id: str) -> ProviderHealth:
        try:
            return self._health[provider_id]
        except KeyError as exc:
            raise ProviderUnavailableError(f"Unknown provider {provider_id!r}", provider_id=provider_id) from exc

    def _is_available(self, spec: ProviderSpec) -> bool:
        health = self._health[spec.id]
        if not health.available:
            return False
        return not health.circuit_open(self._cooldown_seconds)

    def _score(self, spec: ProviderSpec, weights: ProviderScoreWeights) -> ProviderScore:
        health = self._health[spec.id]
        availability = 1.0 if self._is_available(spec) else 0.0
        dimensions = {
            "task_fit": max(0.0, min(1.0, spec.task_fit)),
            "quality": max(0.0, min(1.0, spec.quality)),
            "reliability": max(0.0, min(1.0, spec.reliability)),
            "cost_efficiency": max(0.0, min(1.0, spec.cost_efficiency)),
            "latency": max(0.0, min(1.0, spec.latency)),
            "priority": max(0.0, spec.priority),
            "availability": availability if health.available else 0.0,
        }
        total = (
            dimensions["task_fit"] * weights.task_fit
            + dimensions["quality"] * weights.quality
            + dimensions["reliability"] * weights.reliability
            + dimensions["cost_efficiency"] * weights.cost_efficiency
            + dimensions["latency"] * weights.latency
            + dimensions["priority"] * weights.priority
            + dimensions["availability"] * weights.availability
        )
        return ProviderScore(spec.id, total, dimensions)

    def _instance(self, spec: ProviderSpec) -> ProviderContract:
        with self._lock:
            instance = self._instances.get(spec.id)
            if instance is None:
                instance = spec.factory()
                self._instances[spec.id] = instance
            return instance

    def resolve(
        self,
        capability: ProviderCapability,
        provider_id: str | None = None,
        *,
        weights: ProviderScoreWeights | None = None,
    ) -> ResolvedProvider:
        weights = weights or ProviderScoreWeights()
        if provider_id is not None:
            spec = self._specs.get(provider_id)
            if spec is None:
                raise ProviderUnavailableError(
                    f"Provider {provider_id!r} is not registered. Configure it explicitly or choose an installed provider.",
                    capability=capability,
                    provider_id=provider_id,
                )
            if not spec.supports(capability) or not self._is_available(spec):
                health = self._health[provider_id]
                reason = "does not support the requested capability" if not spec.supports(capability) else "is currently unavailable"
                if health.last_error:
                    reason += f"; last error: {health.last_error}"
                raise ProviderUnavailableError(
                    f"Provider {provider_id!r} {reason}; no silent fallback is performed.",
                    capability=capability,
                    provider_id=provider_id,
                )
            return ResolvedProvider(spec, self._instance(spec), self._score(spec, weights))

        candidates = [
            spec for spec in self._specs.values()
            if spec.supports(capability) and self._is_available(spec)
        ]
        if not candidates:
            raise ProviderUnavailableError(
                f"No available provider supports capability={capability.value!r}. Configure a real provider for this capability.",
                capability=capability,
            )
        ranked = sorted(candidates, key=lambda item: (-self._score(item, weights).total, item.id))
        spec = ranked[0]
        return ResolvedProvider(spec, self._instance(spec), self._score(spec, weights))

    def record_success(self, provider_id: str) -> None:
        health = self.health(provider_id)
        health.consecutive_failures = 0
        health.last_error = None
        health.opened_at = None
        health.available = True

    def record_failure(self, provider_id: str, error: str) -> None:
        health = self.health(provider_id)
        health.consecutive_failures += 1
        health.last_error = error
        if health.consecutive_failures >= self._failure_threshold:
            health.opened_at = monotonic()

    def execute(
        self,
        capability: ProviderCapability,
        payload: Any,
        provider_id: str | None = None,
        *,
        weights: ProviderScoreWeights | None = None,
    ) -> ProviderResult:
        resolved = self.resolve(capability, provider_id, weights=weights)
        try:
            result = resolved.provider.execute(payload)
        except Exception as exc:  # provider boundary: convert transport exceptions to structured failures
            self.record_failure(resolved.spec.id, str(exc))
            raise ProviderUnavailableError(
                f"Provider {resolved.spec.id!r} failed during execution: {exc}",
                capability=capability,
                provider_id=resolved.spec.id,
            ) from exc
        if result.success:
            self.record_success(resolved.spec.id)
        elif result.error_message:
            self.record_failure(resolved.spec.id, result.error_message)
        return ProviderResult(
            success=result.success,
            output=result.output,
            provider_id=resolved.spec.id,
            provider_run_id=result.provider_run_id,
            provenance={
                **result.provenance,
                "provider_id": resolved.spec.id,
                "provider_score": resolved.score.total,
                "provider_score_dimensions": resolved.score.dimensions,
            },
            error_code=result.error_code,
            error_message=result.error_message,
        )
