# Provider Layer Specification

## Scope

The provider layer is the only boundary allowed to know how an external/local AI provider is instantiated or called. Orchestrator code selects a capability and optional explicit provider id; it does not import vendor SDKs.

## Resolution contract

`ProviderRegistry.resolve(capability, provider_id=None)` follows these rules:

1. An explicit `provider_id` is authoritative. If it is missing, disabled, unhealthy, or does not support the requested capability, the request fails with `ProviderUnavailableError`.
2. Without an explicit provider, only registered providers advertising the requested capability are candidates.
3. Candidate adapters are created lazily through their factory.
4. Candidates are ranked using task fit, quality, reliability, cost efficiency, latency, priority, and current availability.
5. No capability is silently substituted with another capability.
6. No provider failure silently routes to an unrelated provider when the caller selected a provider explicitly.

## Health and circuit breaker

Provider transport failures are recorded against the provider. After the configured failure threshold, its circuit opens for a cooldown period. Successful execution resets the failure counter.

A circuit-open provider is not selected during automatic resolution and causes an actionable error when explicitly requested.

## Provenance

Every successful or structured provider response returned by `ProviderRegistry.execute` includes the resolved provider id and routing score in `provenance`. The provider adapter remains responsible for its own provider run id and output metadata.

## Migration rule

The existing `ModelRegistry` remains intact during this wave. This layer is introduced as the contract-first routing boundary so provider adapters can migrate incrementally without a flag-day rewrite. Runtime integration should happen only after the new provider-layer tests and the existing provider tests are green.
