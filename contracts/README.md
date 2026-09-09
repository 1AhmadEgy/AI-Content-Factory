# Canonical Contracts

This directory is the shared contract boundary for Android, backend, workers, providers, QC, rendering, and publishing.

## Rules

- Contracts are transport/domain-neutral and must not depend on Android, Compose, Room, Retrofit, OkHttp, FFmpeg, ComfyUI, or a specific AI provider.
- IDs are opaque strings; timestamps are ISO-8601 UTC.
- `schemaVersion` is required on versioned payloads.
- Job lifecycle: `PENDING → QUEUED → RUNNING → COMPLETED` with `PAUSED`, `RETRYING`, `FAILED`, and `CANCELLED` as controlled states.
- Long-running operations return a job reference rather than blocking the API request.
- Contract changes must remain backward-compatible within a major version and be accompanied by contract tests.

The first implementation artifact is `contracts/v1/job_contract.json`, which is intentionally provider-agnostic and suitable for API validation and test fixtures.
