# Production Coverage Matrix

This document tracks production-hardening coverage for AI Content Factory. The development branch is the source of truth until the pull request is merged.

## Verification gates

- [x] Backend Python syntax validation
- [x] Backend Ruff lint
- [x] Backend automated tests
- [x] Canonical brand asset generation and validation
- [x] Android workflow runs on the development branch push and pull requests
- [x] Android project Gradle validation workflow configured
- [x] Android CI uses a pinned Gradle version without requiring a committed wrapper
- [x] Ephemeral CI signing key generation (never a production/Play key)
- [x] Debug APK, release APK and release AAB artifact validation steps configured
- [x] Release APK signature verification step configured
- [x] PostgreSQL migration numbering is deterministic and unique on the development branch
- [x] Unsafe uploaded-snapshot extraction workflow removed
- [x] Committed project snapshot archive removed from `uploads/`
- [ ] Android CI execution verified green on the current development head
- [ ] Android APK/AAB artifacts downloaded and independently inspected
- [ ] Full provider integration verification with real credentials
- [ ] Full end-to-end production pipeline verification
- [ ] Production signing / Play App Signing configuration (requires owner-controlled secrets and account decisions)

## Queue and scheduling coverage

- [x] Persistent SQLite jobs
- [x] Atomic job leasing and duplicate-claim prevention
- [x] Lease heartbeat and expired-lease recovery
- [x] Idempotent externally-created jobs
- [x] Completion execution fencing
- [ ] Bounded exponential retry backoff with jitter and persisted availability time
- [ ] Full dependency/resource-aware scheduler semantics
- [ ] Project fairness / anti-starvation scheduling
- [ ] Resource reservation lifecycle

## Non-fake production requirements

- Providers must fail with an explicit configuration error when required credentials are absent; no fabricated provider result is acceptable.
- External-provider calls must preserve provenance and actionable, sanitized errors.
- Assets use durable, content-addressed storage with traversal protection.
- Queue execution must preserve idempotency, leases/heartbeats, retries and duplicate-claim prevention.
- Durable state must survive process restart and use migrations/WAL where applicable.
- Production secrets, signing keys and third-party credentials are never committed to the repository.

## Completion rule

A gate is marked complete only after an observable test, build, CI result, or code-level verification supports it. Credentials, production signing material, and irreversible business/account choices remain explicit owner actions.
