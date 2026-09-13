# AI Content Factory — Master Execution Plan

## Operating rule

This document is the execution contract for autonomous repository hardening. Work proceeds by discovery, implementation, verification, and regression testing. Do not replace unavailable production dependencies with mocks or fabricated success.

## Status vocabulary

- `IMPLEMENTED`: code exists and its contract is verified by tests or CI.
- `PARTIAL`: real implementation exists but production coverage/hardening remains.
- `PLANNED`: not implemented.
- `BLOCKED`: requires an external credential, account, or infrastructure resource that cannot safely be invented.

## Execution order

1. Repository and architecture audit.
2. Build/test/lint baseline.
3. Production-integrity audit: mocks, fakes, stubs, placeholders, credentials, insecure transport.
4. Domain/API contract verification.
5. SQLite durability, migrations, indexes, transactions, idempotency.
6. Queue correctness: atomic claim, leases, heartbeat, expiry, retry/backoff, cancellation, stale-worker fencing.
7. Provider registry and routing.
8. Provider resilience: error classification, circuit breaker, failover where multiple real providers exist.
9. Provider cache correctness and maintenance.
10. Asset storage, SHA-256 verification, path containment, provenance.
11. Completion/QC gate for every media-producing worker.
12. Content pipeline dependency correctness.
13. FFmpeg/FFprobe timeout and resource-limit hardening.
14. API authentication, authorization, validation, rate limits, error sanitization, HTTPS policy.
15. Android synchronization, state handling, secure networking, release configuration.
16. CI/CD, Docker, release AAB and signature validation.
17. End-to-end, concurrency, security, and performance verification.
18. Documentation and final production gate.

## Non-negotiable invariants

- No production path returns synthetic content when a provider is unavailable.
- No job reaches `COMPLETED` without durable output and required completion/QC checks.
- No worker may persist a result after losing its execution lease.
- Idempotency is transactionally enforced.
- Asset paths remain inside the configured storage root.
- Asset integrity is verified using SHA-256 before trusted reads/downloads.
- Provider cache identity includes provider, model, job type, target type, target ID, all output-affecting parameters, and seed.
- Secrets never enter source control, APKs, logs, error messages, or Docker images.
- CI success is only reported after the relevant workflow actually completes successfully.
- Production claims require executable evidence, not documentation alone.

## Current priority queue

### P0

- Stale-worker/lease-expiry integration coverage.
- Full scene → provider → QC → subtitle → timeline → render → final-QC integration path.
- Real-provider integration validation when credentials are supplied.
- API authentication/authorization and project-isolation review.
- Complete current CI verification.

### P1

- Provider circuit-breaker/failover coverage.
- Correlation IDs, structured logs, and metrics.
- FFmpeg process timeout/resource-limit tests and benchmark.
- Queue throughput/latency and concurrency tests.
- SQLite query/index/N+1 audit.
- Android synchronization and release-size optimization.

### P2

- Real publishing adapters.
- Asset retention/garbage collection.
- Cost accounting and operational analytics.
- Additional observability dashboards.

## External blockers

Only request human intervention for credentials, signing material, third-party account configuration, or business/store decisions. Until supplied, implement and verify all safe code paths and mark the dependent production capability `BLOCKED` rather than simulating it.
