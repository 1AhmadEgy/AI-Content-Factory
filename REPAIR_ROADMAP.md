# AI Content Factory — Comprehensive Repair & Hardening Roadmap

## Objective

Bring the repository from development state to a continuously tested, recoverable, secure, provider-agnostic production architecture. Runtime success must always represent a real provider/executable result; no mock, fake, simulated, dry-run, timer-based, or fabricated output may be used as production success. See `REAL_ONLY_RUNTIME_POLICY.md`.

## Execution order

### Phase 0 — CI and API baseline
- Fix startup/test-collection failures.
- Run the complete backend test suite on every change.
- Add regression coverage for health/readiness, request IDs, API validation, idempotency, and error envelopes.
- Keep CI green before moving to the next phase.

### Phase 1 — Contract and domain hardening
- Audit API v1 request/response models against the factory pipeline contract.
- Normalize enums, status transitions, IDs, timestamps, pagination, and error codes.
- Add validation for duration, aspect ratio, platform, language, provider/model selection, and job parameters.
- Enforce legal job state transitions and terminal-state behavior.
- Add compatibility tests for OpenAPI/schema behavior.

### Phase 2 — Persistence and migrations
- Audit SQLite schema, indexes, transactions, connection lifecycle, and concurrency behavior.
- Introduce explicit schema versioning/migrations.
- Add indexes for queue leasing, dependencies, project filtering, idempotency, and event queries.
- Verify restart recovery and database integrity.
- Keep storage interfaces provider/storage agnostic.

### Phase 3 — Queue, scheduler, and orchestration
- Verify persistent queue semantics: priority, FIFO tie-breaking, dependencies, retries, timeout, lease, heartbeat, cancellation, and recovery.
- Make job execution idempotent and crash-safe.
- Ensure completed assets survive retries/cancellation.
- Add dependency-cycle detection and dead-letter handling where appropriate.
- Add deterministic integration tests only for pure orchestration/domain behavior; tests must not masquerade as production provider output.

### Phase 4 — Workers and provider abstraction
- Complete worker capability registration and health/lease behavior.
- Separate job orchestration from provider adapters.
- Validate model registry selection by capability, quality, speed, cost, availability, and health.
- Require explicitly configured real providers; an unavailable provider must fail closed with a stable error.
- Do not add fallback behavior that hides real provider failures.

### Phase 5 — Asset, provenance, and storage integrity
- Audit content-addressed storage and checksum verification.
- Ensure every generated asset records provider/model/prompt/job lineage where applicable.
- Add provenance graph queries and cycle protection.
- Add orphan detection/cleanup rules without deleting referenced assets.
- Validate MIME, size, duration, resolution, and file signatures before accepting media.

### Phase 6 — Media pipeline, QC, best-take, timeline, rendering
- Implement/verify image, video, voice, music, SFX, transcription and translation job contracts.
- Add technical/media/continuity/semantic QC contracts.
- Implement deterministic best-take scoring only over real, validated assets.
- Harden timeline validation and renderer job inputs.
- Require real FFmpeg/FFprobe execution for rendering and validate actual outputs.
- Test 16:9, 9:16, 1:1 and 720p/1080p/4K configuration paths.

### Phase 7 — Publishing and repurposing
- Define publication records, states, retries, scheduling, captions, thumbnails, and metadata.
- Keep platform adapters isolated from the core.
- Require an explicitly configured external publishing adapter and an external publication identifier before reporting publication success.
- Never provide a dry-run/mock adapter that reports production success.
- Implement repurposing as derived projects/assets with provenance preserved.

### Phase 8 — Security and operational hardening
- Authentication and project-level authorization.
- Project isolation and ownership checks on every resource path.
- Secrets must come from environment/secret managers, never source code or logs.
- File upload validation, path traversal protection, process isolation, rate limits, audit logs.
- Safe subprocess execution and strict argument construction.
- Security-focused regression tests.

### Phase 9 — Android Control Center
- Audit Android networking/configuration against the versioned API contract.
- Remove hard-coded production endpoints; use environment/build configuration.
- Add authentication/session handling, project list/detail, pipeline controls, job progress, cancellation, QC, render and publication views.
- Keep heavy AI/media execution off-device.
- Development fixtures must remain clearly isolated from production runtime and must never be reported as real execution.

### Phase 10 — Production readiness and documentation
- Add observability: structured logs, request/job correlation IDs, health/readiness, metrics.
- Add deployment profiles for local, Replit/backend-only, and external GPU workers.
- Document architecture, API, worker protocol, provider adapters, storage, recovery, security, and development setup.
- Add release checklist and compatibility policy.
- Mark historical audit/specification documents that describe removed mock behavior as historical, and ensure normative runtime documentation follows `REAL_ONLY_RUNTIME_POLICY.md`.

## Definition of done

1. CI is green and remains green after each phase.
2. No production path reports success from a mock, fake, simulated, timer-based, fabricated, or dry-run provider.
3. A failed worker/job can recover without corrupting or duplicating completed work.
4. Every final output is traceable through timeline, best take, assets, jobs, model/provider, prompts, and inputs.
5. Android acts as a control plane; backend and workers execute the heavy pipeline.
6. Security boundaries and project isolation are enforced by tests.
7. API contracts and deployment/documentation are reproducible from a clean checkout.
8. Missing provider/executable/credential/endpoint/source produces an explicit failure rather than a fabricated substitute.
