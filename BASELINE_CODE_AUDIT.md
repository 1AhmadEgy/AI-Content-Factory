# BASELINE CODE AUDIT — CURRENT

**Audit version:** 2.0  
**Audited ref:** `main` — current repository state at time of this update  
**Purpose:** Replace the obsolete MVP audit with a current engineering baseline.  
**Rule:** This document records implemented behavior only; planned work is explicitly separated from completed work.

---

## 1. Executive Summary

The previous version of this audit is obsolete and has been removed from this file. It described the repository as an Android-only MVP and claimed that the backend, workers, providers, queue, rendering, QC, and publishing layers were absent. That description no longer matches the repository.

The current repository contains a production-oriented Android + FastAPI architecture with real provider integration, durable jobs, workers, assets/provenance, QC, rendering, and publishing boundaries.

Current production flow:

```text
Android Control Plane
        │
        ▼
     FastAPI
        │
        ├── Projects / Series / Episodes
        ├── Durable Jobs + Queue
        ├── Orchestrator / Workers
        ├── Real AI Providers
        ├── Assets + Provenance
        ├── QC + Best Take
        ├── Timeline
        ├── FFmpeg / FFprobe
        └── Publishing
                │
                ▼
            Final Media
```

The repository has also been hardened against fake production success: missing provider credentials, provider failures, invalid AI output, missing media output, failed QC, and missing publishing configuration fail explicitly instead of silently producing simulated success.

---

## 2. Current Repository Baseline

### Implemented major areas

| Area | Current state | Assessment |
|---|---|---|
| Android | Kotlin + Compose + Room + Retrofit/OkHttp | Implemented |
| Backend | FastAPI application | Implemented |
| API | Project/job/media/pipeline endpoints | Implemented |
| Durable jobs | Persistent job records + queue/lease flow | Implemented |
| Orchestration | Worker registry + execution pipeline | Implemented |
| AI providers | Real OpenAI HTTP adapter | Implemented |
| Provider registry | Capability-based production routing | Implemented |
| Story generation | Real provider, schema validation | Implemented |
| Script generation | Real provider, schema validation | Implemented |
| Scene planning | Real provider, schema validation | Implemented |
| Image generation | Real provider output persistence | Implemented |
| TTS | Real provider output persistence | Implemented |
| Assets | Persisted binary/text outputs + validation | Implemented |
| Provenance | Job/output linkage and verification | Implemented |
| QC | Technical media validation and QC gate | Implemented |
| Best Take | Worker boundary present | Implemented |
| Timeline | Timeline worker/boundary | Implemented |
| Rendering | Real FFmpeg/FFprobe boundary | Implemented |
| Publishing | Fail-closed external side-effect boundary | Implemented |
| Country libraries | Additive reusable seed data | Implemented |
| CI | GitHub Actions | Implemented |
| Production documentation | Provider setup / README | Implemented |

---

## 3. Production Integrity Audit

### 3.1 Fake/mock production behavior

The production path must not create fabricated media or report completion without a valid output.

Current baseline:

- Android no longer seeds fake demo projects automatically.
- Android image generation creates a real backend generation job.
- Factory API does not fall back to a mock provider.
- Provider registry requires a real configured provider in production.
- AI story/script/scene generation fails explicitly when the provider is unavailable or returns invalid output.
- Provider worker validates returned asset IDs, project ownership, asset readiness, asset type, and storage verification.
- Media jobs require actual binary output.
- Text jobs require actual text output.
- Completion is guarded by persisted output, provenance, storage verification, and QC.
- Simulated rendering was removed from the production renderer.
- Publishing does not mark a local file as externally published without a real external identifier.

### 3.2 Test doubles

Test doubles are allowed inside tests where they are required to isolate a unit. They must not be registered as production providers or production workers.

This distinction is intentional:

```text
Production  → real providers / real media / real QC
Tests       → explicit test doubles only
```

---

## 4. Provider Architecture

The production provider boundary is now explicit.

### Real provider

`OpenAIAdapter` performs real HTTP requests for:

- text/responses;
- image generation;
- text-to-speech.

Provider configuration is environment-based:

```text
OPENAI_API_KEY
OPENAI_BASE_URL
AICF_PROVIDER_TIMEOUT_SECONDS
AICF_TEXT_MODEL
AICF_IMAGE_MODEL
AICF_TTS_MODEL
```

No API key means no production generation.

### Provider routing

The production registry exposes only enabled and healthy real providers. Text-like capabilities may share the configured real text provider where the capability contract permits it.

The provider worker validates the actual generated asset before accepting the job result.

### Remaining provider scope

Video, LipSync, Music, SFX, and other media capabilities require concrete configured providers before they can be considered production-ready. The architecture contains capability boundaries for them, but an unconfigured capability must fail rather than fabricate output.

---

## 5. AI Generation Integrity

The AI application layer now treats model output as untrusted input.

### Story

The story engine requires:

- an available provider;
- non-empty provider output;
- valid JSON/schema;
- non-empty scenes;
- at least one shot per scene;
- valid library identity references.

Invalid output is an explicit generation error.

### Script

The script engine requires a real provider and validates the generated structure against the requested scene/shot layout. It does not silently return the input story as a fake generated result.

### Scene planner

The scene planner requires a real provider, validates its schema, and preserves required scene/shot counts and durations.

---

## 6. Job Execution Baseline

The executor now treats durable job state as authoritative.

Important guarantees:

- jobs are claimed through the queue/lease mechanism;
- progress events remain observable;
- high-frequency progress persistence is coalesced to reduce unnecessary SQLite writes;
- stage changes persist immediately;
- terminal states are persisted durably;
- completion requires the completion gate;
- failures and retries are represented explicitly.

### Performance change

`AICF_PROGRESS_PERSIST_SECONDS` controls progress persistence coalescing and defaults to `0.5` seconds.

This avoids performing a database write for every high-frequency progress event while retaining progress events for observers.

### Remaining executor review

The following must remain under test:

- lease loss during execution;
- concurrent workers claiming the same job;
- crash recovery;
- retry/backoff correctness;
- cleanup of long-lived progress state;
- completion-gate behavior for every media-producing worker.

---

## 7. Queue / Scheduling Baseline

The repository now contains a durable job/queue architecture rather than an Android-only jobs table.

Implemented concepts include:

- job persistence;
- claiming;
- leases;
- worker resolution;
- worker capability checks;
- retry/failure states;
- scheduled execution;
- specialized worker routing.

The registry explicitly separates `RENDER` from generic provider video generation so a provider capability cannot accidentally claim a render job that belongs to the FFmpeg renderer.

### Performance priorities

The next queue-level optimization targets are:

1. minimize repeated SQLite reads during claim/lease execution;
2. verify indexes used by runnable-job selection;
3. keep claim + lease state transitions atomic;
4. reduce N+1 repository calls;
5. verify bounded concurrency and backpressure;
6. add deterministic lease/retry performance tests.

---

## 8. Asset and Provenance Baseline

Generated outputs are persisted as assets instead of being treated as transient success values.

The provider worker verifies:

```text
asset exists
→ project matches
→ status is READY
→ expected asset type matches
→ storage verification succeeds
```

The completion gate additionally checks provenance and QC before allowing a job to become completed.

This is the required foundation for reliable media lineage and reproducibility.

---

## 9. QC / Completion Gate

The completion gate is a hard production boundary.

A generated job cannot be considered successfully completed merely because a worker returned without an exception.

The gate requires, as applicable:

- output asset IDs;
- persisted asset;
- READY state;
- project ownership;
- provenance linked to the job;
- storage verification;
- QC result;
- no QC blocking condition.

This prevents the previous class of false-positive completion.

---

## 10. Rendering Baseline

Production rendering uses FFmpeg/FFprobe.

The old simulated renderer path has been removed.

Current rendering rules include:

- configurable FFmpeg/FFprobe binaries;
- actual media validation;
- output verification;
- provenance/metadata generation;
- thumbnail generation where configured;
- final media hashing.

The renderer must not manufacture a fake MP4 when FFmpeg or required input media is unavailable.

### Audio integrity

Synthetic silent audio insertion was removed from the production video composition paths reviewed during the hardening work.

A render requiring audio must receive a real audio stream rather than creating one solely to satisfy validation.

---

## 11. Publishing Baseline

Publishing is treated as an external side effect.

The local existence of an MP4 is not sufficient to claim that a platform publication succeeded.

Production publishing therefore requires a real platform adapter and external publication identifier. Missing platform API configuration produces an explicit failure.

This is intentionally fail-closed.

---

## 12. Android Baseline

Android remains a control plane rather than the long-running media worker.

Current important changes:

- automatic fake/demo seeding removed;
- project creation uses the real backend;
- scene generation submits a real backend image-generation job;
- generation failures move the local scene to an explicit failed state instead of fabricating success;
- Room remains responsible for local UI state/cache behavior.

### Android performance follow-up

Recommended next optimization pass:

- reduce broad `SELECT *` flows where screens only need projections;
- verify project-scoped DAO queries and indexes;
- avoid unnecessary repository refreshes after mutations;
- verify Compose state collection does not trigger redundant network synchronization;
- configure release shrinking/minification after compatibility verification;
- measure APK size and startup time before and after optimization.

---

## 13. SQLite / Persistence Performance Baseline

A first startup optimization was applied to reusable country-library seeding: existing library identifiers are loaded in bulk before missing catalog items are inserted, reducing the previous N+1 lookup pattern.

The next persistence audit should focus on:

- SQLite journal/WAL configuration;
- transaction boundaries;
- indexes for job status/priority/availability/lease fields;
- batch inserts and updates;
- repository methods that repeatedly query the same entity;
- bounded result sets and pagination;
- avoiding unnecessary serialization/deserialization cycles.

Performance changes must not weaken lease atomicity, project isolation, provenance, or completion guarantees.

---

## 14. Build / CI Baseline

The repository has GitHub Actions for Android/backend validation and release-oriented builds.

The correct production rule is:

```text
Code change
→ compile
→ lint/static checks
→ unit tests
→ backend tests
→ Android build
→ inspect artifacts
→ only then claim green
```

A workflow being `in_progress` must not be described as passing.

CI failures must be fixed in the implementation or tests; production safeguards must not be weakened merely to make CI green.

---

## 15. Current Known Technical Debt

These items are deliberately recorded as **remaining work**, not as already implemented:

### P0 — verify before production release

- Complete end-to-end provider coverage for every advertised media capability.
- Exercise real provider credentials in an integration environment.
- Validate every worker's completion-gate contract.
- Validate lease loss and worker crash recovery under concurrency.
- Complete API authentication/authorization review for deployment.
- Complete project isolation/security testing.
- Verify full CI matrix is green on the current `main` revision.

### P1 — performance/reliability

- Audit SQLite indexes and transaction boundaries.
- Remove remaining N+1 database access patterns.
- Reduce redundant FFprobe/FFmpeg work.
- Add queue throughput/latency measurements.
- Add deterministic performance tests for job execution.
- Audit Android synchronization and Compose recomposition cost.
- Evaluate release minification/shrinking and measure APK impact.

### P2 — operational maturity

- Provider cost accounting.
- Richer analytics/learning feedback loops.
- More publishing-platform adapters.
- Retention and garbage-collection policies for generated assets.
- Operational dashboards and tracing.

---

## 16. Audit Rules Going Forward

This file should be updated after meaningful architecture changes.

Do not write statements such as:

- “implemented” when only a stub exists;
- “production ready” when credentials/tools were not exercised;
- “published” without a real external platform identifier;
- “completed” without the completion gate;
- “optimized” without a measured or testable improvement;
- “CI green” while a relevant workflow is still running or failing.

Use these labels instead:

```text
IMPLEMENTED  = code exists and has a verified contract/test
PARTIAL      = boundary exists but capability is incomplete
PLANNED      = not implemented yet
BLOCKED      = cannot run because a required external dependency/configuration is absent
```

---

## 17. Final Baseline

The repository is no longer accurately described as an Android-only MVP shell.

The current baseline is a **production-oriented Android + FastAPI content-generation pipeline with real-provider and fail-closed boundaries**, with performance and operational hardening still in progress.

The priority is now to improve correctness, latency, throughput, resource usage, and deployment reliability **without reintroducing fake production behavior**.
