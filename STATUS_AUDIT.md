# AI Content Factory — STATUS AUDIT

Date: 2026-09-11

## Audit rule

This audit distinguishes implemented production paths from partial safeguards and documentation-only plans. A component is not considered production-complete merely because its interface exists.

Legend:
- ✅ Production: real implementation with failure handling and production acceptance checks.
- ⚠️ Partial: real implementation exists but important production hardening, integration, or coverage remains.
- ❌ Paper: specification/documentation exists without an implemented production path.

## Major modules

| Area | Status | Evidence / finding | Next action |
|---|---|---|---|
| `backend/app/domain/` | ✅ | Domain contracts/entities exist and are used by orchestration and repositories. | Keep contracts authoritative. |
| `backend/app/infrastructure/sqlite.py` | ✅ | SQLite persistence, transactions, idempotency records, CAS-style job updates. | Add/expand migration/version validation. |
| `backend/app/infrastructure/sqlite_queue.py` | ✅ | Atomic lease claim, targeted claim, heartbeat, lease expiry recovery, retry budget. | Expand concurrent execution tests. |
| `backend/app/orchestrator/queue.py` | ✅ | Queue/worker abstraction isolates execution from queue backend. | Preserve as broker boundary; avoid competing queue. |
| `backend/app/orchestrator/job_executor.py` | ⚠️ | Execution is fenced by attempt and checks active lease before persistence; broader stale-worker integration coverage is still needed. | Add expiry/reclaim integration tests. |
| `backend/app/orchestrator/content_pipeline.py` | ⚠️ | Real image/TTS/subtitle/timeline orchestration exists; integration paths need full end-to-end coverage. | Verify scene → timeline → render transitions. |
| `backend/app/orchestrator/production_pipeline.py` | ⚠️ | Additional language/lipsync orchestration exists; competing/overlapping transitions require integration coverage. | Audit dependency transitions and idempotency. |
| `backend/app/providers/` | ⚠️ | Provider registry and OpenAI adapter use real HTTP/API behavior; broader provider failover and circuit breaking are not complete. | Add provider resilience layer. |
| `backend/app/providers/openai_adapter.py` | ✅ | Real text/image/TTS HTTP calls; no synthetic media fallback. | Add shared cache and resilience. |
| `backend/app/providers/registry.py` | ⚠️ | Explicit model configuration and health filtering exist; failover policy is not yet a complete circuit-breaker implementation. | Implement provider breaker at provider boundary. |
| `backend/app/workers/provider_worker.py` | ✅ | Validates real provider outputs, assets, project ownership, readiness, and storage checksums. | Add broader failure/retry tests. |
| `backend/app/workers/render_worker.py` | ✅ | Real FFmpeg/FFprobe rendering, media validation, content-addressed output, cancellation. | Add resource/time-limit coverage and benchmark. |
| `backend/app/workers/media_document_worker.py` | ⚠️ | Real subtitle, thumbnail, metadata, and QC document/media operations exist. | Harden initialization and integration coverage. |
| `backend/app/workers/qc_worker.py` | ✅ | Real filesystem/asset QC path exists and fails closed on invalid assets. | Integrate quantitative Take scoring without duplicating QC responsibilities. |
| `backend/app/domain/qc.py` | ⚠️ | Canonical QC findings/decision model exists. | Extend for quantitative best-take scoring where required. |
| `backend/app/rendering/media_qc.py` | ✅ | Media-level validation thresholds and FFprobe-backed checks exist. | Expand test matrix. |
| `backend/app/infrastructure/storage.py` | ✅ | Content-addressed local storage with SHA-256 and verification. | Add orphan/recovery checks. |
| `backend/app/workers/publish_worker.py` | ⚠️ | Publication package and source validation are real; external platform adapters currently fail closed when not configured. | Implement real platform integrations incrementally. |
| `backend/app/publishing/adapters.py` | ⚠️ | Adapter contract and fail-closed defaults exist; external publishing is not yet implemented. | Add one real platform adapter at a time. |
| `backend/app/api/` | ⚠️ | `/api/v1` API layer exists; production-wide integration and idempotency coverage remain. | Complete API integration tests. |
| Android `app/` | ⚠️ | Android control client exists; backend URL fallback was removed, but repository/cache/paging audit remains. | Audit Room/Paging/cache and production fallbacks. |
| `backend/tests/` | ⚠️ | Queue, provider configuration, executor, and production guard tests exist. | Add concurrent stale-worker and end-to-end pipeline tests. |
| `docs/` + `specs/` | ✅ | Specifications document architecture and production acceptance rules. | Keep specs; do not replace implementation with parallel architecture. |

## Three critical risk areas

### 1. Duplicate Job execution

**Finding: mitigated in the current architecture.**

The repository already has a SQLite queue with transactional claiming and per-job leases. A job cannot be claimed twice while its active lease exists. Lease expiry returns the job to retry/recovery according to the retry budget. Idempotency keys also exist at job creation.

Remaining risk: a stale worker must never persist results after another worker has reclaimed the job. The repository exposes compare-and-set job persistence using the execution attempt, and the executor checks lease ownership. This now needs explicit integration tests covering lease expiry → reclaim → stale write rejection.

**Decision:** do not introduce a second ARQ/Redis queue as a parallel source of truth. If a broker is introduced later, it must implement the existing `JobQueue` contract or replace the queue deliberately in a migration.

### 2. Provider failure / circuit breaking

**Finding: partial.**

Providers fail closed rather than returning synthetic outputs. Provider configuration is explicit and the OpenAI adapter performs real HTTP calls. Automatic circuit breaking and cross-provider failover are not yet a completed production capability.

**Action:** implement a provider-level resilience policy around the existing registry/adapter boundary. Shared breaker state must use safe ownership semantics and must not allow stale workers to corrupt breaker state.

### 3. FFmpeg timeout / resource limits

**Finding: substantially implemented, but hardening remains.**

The current render worker uses real FFmpeg/FFprobe, validates inputs and output, and supports cancellation. It is not acceptable to replace this with a second simplified render worker. Production hardening should add explicit process timeout/resource-limit tests and benchmark the existing renderer before changing encoding defaults.

## Architecture decision

The supplied ARQ/PostgreSQL example is **not copied verbatim** because it creates a competing job schema and execution lifecycle. The repository already has a persistent SQLite queue, leases, idempotency, worker lifecycle, execution fencing, asset validation, and a completion gate. Introducing a second queue before migrating the existing contract would increase duplicate-execution risk rather than reduce it.

PostgreSQL/Redis/ARQ may be introduced later as an explicit infrastructure migration, not as a parallel hidden queue.

## Immediate repair order

1. Finish stale-worker/lease integration tests.
2. Verify complete scene → provider → QC → subtitle → timeline → FFmpeg → final QC path.
3. Add provider cache using the existing provider boundary.
4. Add provider circuit breaker/failover.
5. Add structured correlation IDs/logging and metrics.
6. Benchmark and harden FFmpeg resource limits.
7. Add end-to-end and concurrent load tests.

## Acceptance rule

A job is production-complete only when its output assets are real, readable, project-scoped, provenance-valid, checksum-verified, and accepted by the completion/QC gate. A status flag, timer, placeholder file, or synthetic provider response is not evidence of completion.
