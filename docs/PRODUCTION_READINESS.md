# Production Readiness

This document is evidence-driven. A checkbox is marked complete only when the repository contains an executable test, workflow gate, or documented operational verification for it.

## M0 — Correctness

- [x] SQLite claim exclusivity under real concurrent connections
  - Evidence: `backend/tests/integration/test_sqlite_queue_leases.py`
- [x] Lease reclaim creates a new lease and attempt
  - Evidence: `backend/tests/integration/test_sqlite_queue_leases.py`
- [x] Stale update/heartbeat/attempt fencing
  - Evidence: `backend/tests/integration/test_sqlite_queue_leases.py`
- [x] Executor rejects completion after lease loss
  - Evidence: `backend/tests/test_job_executor.py`
- [x] Worker receives a fail-closed lease guard
  - Evidence: `backend/app/orchestrator/queue.py`, `backend/app/orchestrator/job_executor.py`
- [x] Content-addressed storage supports a guarded commit point
  - Evidence: `backend/app/infrastructure/storage.py`
- [x] Render performs a lease check at the storage commit boundary
  - Evidence: `backend/app/workers/render_worker.py`
- [x] Asset creation is idempotent and rejects conflicting ID reuse
  - Evidence: `backend/app/infrastructure/asset_repository.py`, `backend/tests/test_asset_repository.py`
- [x] Provider HTTP/transport failures are classified consistently across urllib/httpx
  - Evidence: `backend/app/infrastructure/error_classifier.py`, `backend/tests/test_error_classifier.py`

## M1 — CI and Security

- [x] Backend tests and lint run on pull requests
  - Evidence: `.github/workflows/ci.yml`
- [x] Android unit tests, lint, and debug build run on pull requests
  - Evidence: `.github/workflows/ci.yml`
- [x] Docker build runs on pull requests without pushing
  - Evidence: `.github/workflows/ci.yml`
- [x] Main branch Docker builds can publish to GHCR
  - Evidence: `.github/workflows/ci.yml`
- [x] CodeQL covers Python and Java/Kotlin
  - Evidence: `.github/workflows/security.yml`
- [x] Dependency Review runs on pull requests
  - Evidence: `.github/workflows/security.yml`
- [x] Workflow permissions are least-privilege scoped
  - Evidence: workflow job permissions
- [x] CI does not use production provider secrets
  - Evidence: deterministic test environment in `.github/workflows/ci.yml`
- [x] Test-mode authentication bypass is confined to `AICF_ENV=test`
  - Evidence: `backend/app/main.py`, `backend/tests/test_api_key_auth.py`
- [x] Critical workflows/backend/Docker/Android paths have CODEOWNERS coverage
  - Evidence: `.github/CODEOWNERS`

## M1 — Container baseline

- [x] Runtime container uses a non-root user
  - Evidence: `backend/Dockerfile`
- [x] Container has a healthcheck
  - Evidence: `backend/Dockerfile`
- [x] Docker build enables SBOM/provenance generation
  - Evidence: `.github/workflows/ci.yml`
- [ ] Deployment consumes immutable image digests
- [ ] Runtime filesystem/resource limits are enforced by deployment

## M2 — Supply chain and release

- [ ] Actions are pinned to immutable SHAs
- [ ] Artifact attestations are verified
- [ ] Signed Android release artifact
- [ ] AAB/APK release packaging and checksums
- [ ] Immutable Docker release tags
- [ ] GitHub Release automation

## M3 — Operations

- [ ] Formal database migrations
- [ ] Backup and restore test
- [ ] Metrics and structured operational dashboards
- [ ] External publish UNKNOWN/reconciliation state
- [ ] Asset garbage collection
- [ ] Recovery drill covering worker crash after side effects

## Deferred architectural decisions

- Tenancy model remains explicitly undecided; no multi-tenant authorization model is invented here.
- Release target remains explicitly undecided; no automatic production release workflow is enabled.
- PostgreSQL/Redis/Kubernetes remain deferred until correctness and operational evidence justify them.
