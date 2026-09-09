# Backend Foundation

The backend is the authoritative orchestration boundary for long-running content-generation work.

## Responsibilities

- Own authenticated API v1 requests.
- Persist projects, jobs, assets, QC results, timelines, and publishing state.
- Enqueue and schedule durable jobs.
- Dispatch jobs to workers through provider-agnostic interfaces.
- Validate outputs before marking jobs complete.
- Keep Android as a control client; Android must not execute heavy AI, FFmpeg, or GPU workloads.

## Initial implementation boundary

The repository currently contains an Android prototype and no production backend. This directory establishes the backend boundary without coupling it to Android implementation details. The next P0 steps are a minimal backend runtime, persistence, API v1 health/readiness endpoints, and a deterministic mock job path.

Do not add provider-specific orchestration to API handlers. Provider/model selection belongs behind the worker/provider and model-registry boundaries.
