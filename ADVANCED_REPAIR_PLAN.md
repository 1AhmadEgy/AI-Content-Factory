# AI Content Factory — Advanced Repair & Development Plan

**Baseline:** `main` at `e5bc9cbfa8bb5a25552bb12d5ead5d785fba193d`
**Strategy:** incremental hardening; preserve the current MVP until replacement behavior is tested.

## Wave 1 — Safety and Contract Gate
- Freeze the baseline with a dedicated branch/tag.
- Treat `CONTRACTS_SPECIFICATION.md` as normative and resolve the Job lifecycle discrepancy before expanding implementation.
- Add schema/version discipline and serialization round-trip tests.
- Add CI gates for contracts, backend tests, Android tests, lint, and dependency/security checks.

## Wave 2 — Backend Boundary
- Introduce `backend/api`, `backend/domain`, `backend/orchestrator`, `backend/queue`, `backend/workers`, `backend/providers`, `backend/qc`, `backend/storage`.
- Start with FastAPI health/readiness and `/api/v1/projects`.
- Use deterministic development storage first, with interfaces ready for PostgreSQL.
- Standardize Envelope, request IDs, structured errors, and `Idempotency-Key`.

## Wave 3 — Android Domain Boundary
- Split pure domain models from Room entities and remote DTOs.
- Add UseCases and repository interfaces.
- Remove silent network fallback and repository-side job simulation only after equivalent tests exist.
- Make backend authoritative for job lifecycle.

## Wave 4 — Durable Execution
- PostgreSQL migrations from the current Room schema.
- Persistent jobs, dependencies, events, leases, heartbeats, retries, cancellation, and crash recovery.
- Project-scoped authorization and queries.

## Wave 5 — Deterministic Worker / Asset / QC Proof
- Worker creates a real deterministic asset.
- Record provenance and SHA-256 integrity.
- Run technical QC before success.
- Select Best Take only from QC-passed assets.
- Add Golden E2E and failure-injection tests.

## Wave 6 — Provider and Model Architecture
- Model/ModelVersion/Provider/Capability registry.
- Provider adapters behind a stable interface.
- Add one real provider first; adding a second must not require Orchestrator changes.

## Wave 7 — Timeline and Rendering
- Versioned timeline, tracks/clips, audio/subtitles, render plans.
- Deterministic renderer first, FFmpeg behind `RenderWorker`.
- Validate output before marking render complete.

## Wave 8 — Publishing and Operations
- One platform adapter with durable idempotent publishing.
- Observability, audit events, cost records, retention, backups, rate limits, and operational runbooks.

## Non-negotiable invariants
1. No timer can create success.
2. No silent network fallback can create production state.
3. No asset is accepted without provenance and integrity metadata.
4. No Best Take without a linked passing QC result.
5. No cross-project query without authorization.
6. No provider/model hard-coding in Compose or Orchestrator.
7. No schema replacement without migration tests.
8. Every critical workflow has an automated regression test.

## Working rule
Each wave must leave `main` buildable and the MVP behavior covered. Changes land through small, reviewable commits/PRs rather than a large rewrite.
