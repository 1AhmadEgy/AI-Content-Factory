# Development Audit — 2026-09-10

## Baseline

Repository: `1AhmadEgy/AI-Content-Factory`
Branch: `main`

The current repository is an Android-first MVP shell. The engineering specifications already define a larger production architecture, but the implementation is missing the backend, durable queue, workers/providers, assets/provenance, QC, timeline/rendering, publishing, and model-registry layers.

## Critical findings

1. `Repository.kt` performs network fallback, mock generation, job progression, and approval transitions inside the Android repository.
2. `FactoryApiService.kt` still targets `/api/...` while the normative API contract requires `/api/v1/...` and standard envelopes/errors.
3. `NetworkClient.kt` hard-codes `http://10.0.2.2:8000/`.
4. Room queries are global rather than project-scoped and there is no production migration strategy.
5. `GenerationJob` is not contract-complete and lacks durable event/dependency/idempotency/lease information.
6. The repository contains no backend implementation despite a backend CI workflow.
7. Tests are mostly scaffolding and do not exercise the required pipeline contracts.

## Development strategy

### Phase 1 — Foundation
- Add a minimal FastAPI backend implementing the normative `/api/v1` envelope and health/readiness endpoints.
- Add project CRUD and durable-shaped job APIs with deterministic in-memory storage for development.
- Add idempotency handling for job creation.
- Add backend unit/API tests.
- Keep Android behavior unchanged until the backend contract is verified.

### Phase 2 — Android boundary
- Introduce domain interfaces/use cases.
- Replace repository-side silent network fallback with explicit offline/mock mode.
- Move job lifecycle authority to the backend.
- Add request IDs, idempotency keys, structured API errors, and `/api/v1` routes.

### Phase 3 — Persistence and queue
- Implement PostgreSQL schema and migrations.
- Add job dependencies, events, leases, retries, worker heartbeats, and recovery.

### Phase 4 — Workers/providers
- Implement provider adapters and worker contracts for LLM, image, video, TTS, audio, upscale, and render.

### Phase 5 — Assets/QC/timeline/publishing
- Implement content-addressed assets and provenance, QC gates, best-take selection, timeline versions, rendering, and publishing workflows.

## Acceptance rule

Do not mark a generation job `COMPLETED` or a scene `APPROVED` merely because a timer finished. Completion must follow valid worker output and required QC gates.
