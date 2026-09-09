# BASELINE CODE AUDIT

**Audit version:** 1.0  
**Audited ref:** `main` at `980013f7065885abc2aba315e0eb3e6b9d657d23`  
**Scope:** repository structure, Android `app/`, persistence, networking, architecture, tests, and alignment with the approved engineering specifications.

---

## 1. Executive Summary

The repository is currently an **Android-first MVP shell**, not yet the target local-first AI Content Factory architecture.

The current implementation has a usable starting point for:

- Android Compose UI;
- local Room persistence;
- basic Project → Series → Episode → Scene → Shot entities;
- a basic GenerationJob entity;
- Retrofit/Moshi networking;
- a repository layer;
- a simple simulated generation flow;
- basic unit/instrumentation test scaffolding.

However, the target architecture requires a distributed production pipeline:

```text
Android
 → API
 → Backend
 → Persistent Queue
 → Workers
 → Providers/Models
 → Assets/Provenance
 → QC/Continuity
 → Timeline
 → Renderer
 → Publishing
 → Analytics/Learning
```

The current repository does not yet contain the required backend, worker, provider, queue, asset, QC, timeline, renderer, publishing, analytics, model registry, or orchestration implementation.

The largest architectural blocker is that production behavior currently lives inside the Android `Repository`, including network fallback, mock generation, job progress simulation, and state mutation. This conflicts with the approved boundary that Android is a control plane and heavy/long-running work belongs outside the Android application.

---

## 2. Repository Inventory

The audited tree contains the Android application plus documentation/workspace material. The current top-level implementation includes:

```text
app/
  build.gradle.kts
  src/main/
    AndroidManifest.xml
    java/com/example/
      ContentFactoryApp.kt
      MainActivity.kt
      core/model/Models.kt
      core/theme/*
      data/local/*
      data/remote/*
      data/repository/Repository.kt
      feature/FactoryViewModel.kt
      feature/Screens.kt
    res/*
  src/test/*
  src/androidTest/*

build.gradle.kts
gradle.properties
gradle/libs.versions.toml
settings.gradle.kts

public/
workspace/docs/

Engineering specifications at repository root.
```

The recursive repository tree shows **no `backend/` implementation directory** and no implementation directories for workers, providers, queue, QC, rendering, publishing, model registry, or orchestration. The repository therefore cannot currently execute the intended end-to-end factory outside the Android MVP. fileciteturn0file0L2-L11

---

## 3. Current Android Architecture

Current flow:

```text
MainActivity
   ↓
FactoryViewModel
   ↓
Graph.repository
   ↓
Repository
   ├── Room / FactoryDao
   └── Retrofit / NetworkClient
```

`MainActivity` owns navigation and constructs a `FactoryViewModel`; the navigation currently covers Projects, Project Detail, Series Detail, Episode Detail, and Queue. fileciteturn2file0L2-L6

`FactoryViewModel` directly exposes repository `StateFlow`s for projects, series, episodes, scenes, and jobs, and directly invokes repository operations. fileciteturn5file0L2-L6

`ContentFactoryApp` initializes the application-wide `Graph` singleton and therefore establishes a global repository instance. fileciteturn6file0L2-L6

### Assessment

**Status: PARTIAL / P1 architectural debt**

The basic separation is recognizable, but the target architecture requires:

```text
UI
 → ViewModel
 → UseCase
 → Repository interface
 → Data source
```

and the Domain layer MUST remain independent of Android/Data implementation details.

The current implementation has no visible use-case layer and no explicit domain repository interfaces.

---

## 4. Domain Model Audit

Current models are concentrated in one `Models.kt` file and mix Room entities, JSON/API annotations, and request DTOs. fileciteturn1file0L2-L6

Existing entities include:

- Project
- Series
- Episode
- Scene
- Character
- Location
- Shot
- GenerationJob

This is a useful MVP foundation.

### Major deviations

The approved contracts require a much richer domain:

```text
Project
Series
Season
Episode
Story
StoryBeat
Character
CharacterBible
CharacterAsset
World
Location
Scene
Shot
Dialogue
Voice
Asset
GenerationJob
ProviderRun
QcResult
BestTake
Continuity
Timeline
RenderJob
PublishingJob
AnalyticsRecord
LearningPattern
CostRecord
```

Many required entities are absent.

### GenerationJob

The current `GenerationJob` contains basic job fields, but it is not contract-complete. It lacks important fields such as:

- project ID;
- parent job ID;
- schema-versioned input/output contracts;
- explicit error code/error message separation;
- updated timestamp;
- dependency representation;
- provider-run linkage;
- persistent event history;
- idempotency key;
- lease/worker information;
- richer retry/fallback state.

The current status enum also uses `CREATED`, while the approved lifecycle starts with `PENDING` and uses the canonical shared contract vocabulary.

**Severity: P0**

---

## 5. Persistence Audit

Room is present and currently contains eight entities. The database is version `1`, with `exportSchema = false`. fileciteturn2file0L2-L6

`FactoryDao` provides broad `SELECT *` flows and insert/update methods for the current MVP entities. fileciteturn1file0L2-L6

### Problems

1. No migrations are visible for the target schema.
2. No asset/provenance tables.
3. No job dependency/event/provider-run tables.
4. No QC/best-take/continuity tables.
5. No timeline/render tables.
6. No publishing/account/analytics tables.
7. No explicit project-isolation strategy.
8. No idempotency/concurrency persistence.
9. DAO queries are not project-scoped.
10. `SELECT *` is used without explicit query projections or filters.

**Severity: P0**

### Important rule

Do not replace the current database with a new schema blindly. First preserve the existing data model through explicit migrations and tests.

---

## 6. Repository Audit

`Repository.kt` currently combines:

- local persistence;
- remote API calls;
- offline fallback;
- mock data seeding;
- generation orchestration;
- job simulation;
- scene state transitions;
- logging.

The repository uses a global coroutine scope and directly references the network singleton. fileciteturn3file0L2-L6

### Critical finding

The current implementation does this pattern:

```text
Network call fails
      ↓
Repository silently creates local object
      ↓
Production state continues
```

This is useful for a demo but is not acceptable as the production architecture because failures can become indistinguishable from successful backend operations.

The repository also simulates job progress using delays and eventually marks the job `COMPLETED`, then marks the scene `APPROVED`. fileciteturn3file0L2-L6

This violates the approved rule that a job may become `COMPLETED` only after a real or deterministic mock worker has produced a valid output and required QC has passed.

**Severity: P0**

---

## 7. Networking Audit

`FactoryApiService` currently exposes only a small set of endpoints:

```text
createProject
createSeries
createEpisode
createScene
generateScene
getJob
```

and uses routes such as `api/projects` and `api/scenes/{scene_id}/generate`. fileciteturn4file0L2-L6

The approved API specification requires `/api/v1/...`, standardized envelopes, authentication headers, request IDs, idempotency, structured errors, pagination, job events/SSE, and much broader resources.

`NetworkClient` currently hard-codes `http://10.0.2.2:8000/` as the base URL. fileciteturn5file0L2-L6

### Gaps

- no `/api/v1` contract;
- no auth interceptor;
- no request ID propagation;
- no idempotency-key support;
- no standard error envelope;
- no SSE/event stream;
- no API version abstraction;
- no environment-specific endpoint configuration;
- no typed API error mapping.

**Severity: P0**

---

## 8. Backend Audit

No backend implementation directory is present in the audited tree. The existing Android client therefore has no repository-contained implementation of the target backend/orchestrator boundary. fileciteturn0file0L2-L11

Missing:

```text
backend/api
backend/domain
backend/orchestrator
backend/queue
backend/workers
backend/providers
backend/qc
backend/rendering
backend/storage
```

**Severity: P0 — primary implementation blocker**

---

## 9. Worker / Provider Audit

No production worker/provider implementation is present in the current repository tree.

Missing worker categories include:

- LLM;
- image;
- video;
- TTS;
- LipSync;
- music;
- SFX;
- upscale;
- interpolation;
- render.

Missing provider abstractions include:

- generic HTTP provider;
- CLI provider;
- local model provider;
- ComfyUI adapter;
- model adapter;
- resource manager;
- provider health/capability checks;
- cancellation/progress contracts.

**Severity: P0**

---

## 10. Model Registry Audit

No model registry implementation is present.

Required but absent:

```text
Model
ModelVersion
Provider
Capabilities
HardwareRequirements
Runtime
License
ModelHealth
ModelRouter
FallbackPolicy
```

This is a prerequisite for adding Wan/video models, local LLMs, ComfyUI workflows, TTS, LipSync, music, SFX, and upscalers without hard-coding a provider.

**Severity: P1**

---

## 11. Queue / Scheduler Audit

The current Android `jobs` table is not a persistent distributed queue.

There is no implementation for:

- dependency graph;
- runnable-job calculation;
- priority/aging;
- fairness;
- leases;
- worker registration;
- heartbeat;
- resource reservation;
- GPU/VRAM scheduling;
- retry backoff/jitter;
- crash recovery;
- backpressure;
- multi-worker dispatch.

`IMPLEMENTATION_STATUS.md` itself records Queue as not implemented and Mock Workers as the next step. fileciteturn8file0L2-L6

**Severity: P0**

---

## 12. Asset / Provenance Audit

No target Asset/Blob/Provenance implementation is visible in the current tree.

Required:

```text
Asset
Blob
AssetProvenance
AssetLineage
StorageProvider
IntegrityCheck
Thumbnail
Preview
Retention
GarbageCollection
```

This is a fundamental blocker for AI-generated images/videos/audio because generated outputs cannot be treated as transient strings or database fields.

**Severity: P0**

---

## 13. QC / Continuity Audit

No target QC pipeline is implemented.

Missing:

- integrity QC;
- technical media QC;
- semantic QC;
- continuity QC;
- audio/lip-sync QC;
- license/policy QC;
- scoring/confidence;
- hard blockers;
- human review state;
- best-take selection;
- regeneration policy.

Current code directly moves a simulated scene from pending to approved after simulated job completion, without the required QC gate. fileciteturn3file0L2-L6

**Severity: P0**

---

## 14. Timeline / Rendering Audit

No timeline or renderer implementation is present.

Missing:

- timeline versions;
- integer timebase;
- tracks/clips;
- transitions;
- transforms/keyframes;
- audio mixing;
- subtitle tracks;
- render profiles;
- render plans;
- FFmpeg boundary;
- render worker;
- output validation;
- render caching;
- deterministic render tests.

**Severity: P0**

---

## 15. Publishing Audit

No publishing implementation is present.

Missing:

- Publication Plan;
- Publishing Job;
- platform account references;
- platform adapters;
- metadata versions;
- captions;
- thumbnails;
- scheduling;
- upload sessions;
- idempotency;
- remote verification;
- platform events;
- analytics collection.

The newly approved publishing specification defines publishing as a durable external-side-effect workflow rather than a UI API call. The current code has none of this boundary yet.

**Severity: P2 after core pipeline**

---

## 16. Security Audit

Positive:

- a `.env.example` exists;
- the Gradle Secrets plugin is configured.

However, the current network endpoint is hard-coded and there is no visible authentication architecture. The Gradle configuration also includes a release signing configuration whose keystore path defaults to a repository-relative filename if no environment variable is supplied. fileciteturn7file0L2-L6

Required next checks before production:

- remove hard-coded runtime endpoints;
- define environment/config precedence;
- implement authentication;
- add project authorization;
- add credential/secret boundary;
- prevent sensitive data in logs;
- review backup/export behavior;
- verify signing-key handling;
- add security-focused tests.

**Severity: P0/P1 depending on deployment target**

---

## 17. Build / Dependency Audit

The Android module is configured for Compose, Room, Retrofit, Moshi, coroutines, tests, KSP, and several optional integrations. Release minification is currently disabled. fileciteturn7file0L2-L6

The project currently has useful foundations, but production readiness requires:

- reproducible builds;
- CI build verification;
- dependency locking/update policy;
- release signing policy;
- lint/static analysis;
- security scanning;
- test coverage thresholds;
- release artifact validation.

No production claim should be made until CI and a full build/test matrix are verified.

**Severity: P1**

---

## 18. Test Audit

Current tests are largely example scaffolding:

```text
ExampleUnitTest.kt
ExampleRobolectricTest.kt
ExampleInstrumentedTest.kt
```

The tree does not show the contract/unit/integration/golden pipeline suite required by the engineering specifications. fileciteturn0file0L2-L11

Required test layers:

```text
Domain unit tests
Database tests
Repository tests
API contract tests
Job state-machine tests
Queue tests
Worker contract tests
Provider adapter tests
Asset integrity tests
QC tests
Timeline tests
Render tests
Publishing adapter tests
Security/isolation tests
Golden E2E
Failure injection
```

**Severity: P0 for production pipeline; P1 for current UI MVP**

---

## 19. Architecture Gap Matrix

| Area | Current | Target | Gap | Priority |
|---|---|---|---|---|
| Android UI | Present | Control plane | Partial | P1 |
| ViewModel | Present | UI state boundary | Partial | P1 |
| UseCases | Missing | Required | Major | P0 |
| Domain layer | Missing/merged | Independent domain | Major | P0 |
| Repository interfaces | Missing | Required | Major | P0 |
| Room | Basic | Production schema | Major | P0 |
| API client | Basic | `/api/v1` contract | Major | P0 |
| Auth | Missing | Required | Major | P0 |
| Backend | Missing | Required | Critical | P0 |
| Orchestrator | Missing | Required | Critical | P0 |
| Queue | Missing | Persistent distributed queue | Critical | P0 |
| Workers | Mock simulation only | Real worker contracts | Critical | P0 |
| Providers | Missing | Adapter architecture | Critical | P0 |
| Model Registry | Missing | Required | Major | P1 |
| Assets | Missing | CAS/provenance | Critical | P0 |
| QC | Missing | Multi-layer QC | Critical | P0 |
| Continuity | Missing | Series memory/continuity | Major | P1 |
| Timeline | Missing | Versioned timeline | Critical | P0 |
| Renderer | Missing | FFmpeg abstraction | Critical | P0 |
| Publishing | Missing | Durable adapter workflow | P2 |
| Analytics | Missing | Normalized records | P2 |
| Learning | Missing | Optimization layer | P3 |
| License Guard | Missing | Required gate | P1 |
| Observability | Minimal logging | Structured tracing/metrics | Major | P1 |
| Tests | Example tests | Contract + Golden E2E | Critical | P0 |

---

## 20. P0 Findings — Must Fix Before Feature Expansion

### P0-01 — Establish real backend boundary

Create the backend foundation before adding heavy AI integrations.

### P0-02 — Separate domain from data/API/UI

Stop using one model file as Room entities + API DTOs + domain models.

### P0-03 — Replace repository-owned orchestration

Generation workflow must move to use cases/orchestrator/backend jobs.

### P0-04 — Implement canonical job contract

Introduce shared statuses, IDs, timestamps, input/output schemas, dependencies, provider runs, errors, events, idempotency, and lifecycle rules.

### P0-05 — Implement persistent queue

Queue must be server-side/persistent and recoverable.

### P0-06 — Implement deterministic mock worker

The mock worker becomes the first real worker implementation and must produce a real mock asset plus provenance and QC result.

### P0-07 — Implement asset system

No generation pipeline should depend on `output: String` as the final artifact representation.

### P0-08 — Implement QC gate

Jobs must not become successful merely because a timer reached 100%.

### P0-09 — Establish API v1 contract

Migrate client/server communication to the approved versioned API envelope.

### P0-10 — Establish Golden E2E

The first milestone should prove:

```text
Project
 → Episode
 → Scene
 → Shot
 → Job
 → Mock Worker
 → Asset
 → QC
 → Best Take
```

before real AI models are added.

---

## 21. Recommended Implementation Sequence

### Stage 0 — Freeze the Baseline

Do not perform a large refactor yet.

Record this audit as the baseline and preserve the current application behavior.

### Stage 1 — Foundation

Implement:

```text
backend/
contracts/
domain/
```

Introduce canonical IDs, timestamps, errors, jobs, assets, QC, and API envelopes.

### Stage 2 — Database

Add backend persistence/migrations according to `DATABASE_SCHEMA_SPECIFICATION.md`.

Keep Android Room as a local cache/offline store rather than the distributed source of truth.

### Stage 3 — Job Engine

Implement:

```text
Job Repository
Job State Machine
Dependencies
Queue
Scheduler
Leases
Retry Policy
Events
```

### Stage 4 — Mock Worker

Implement the first end-to-end worker using deterministic output.

### Stage 5 — Asset + QC

Make asset integrity and QC mandatory completion gates.

### Stage 6 — Timeline + Renderer

Build a deterministic mock renderer first, then FFmpeg adapter.

### Stage 7 — AI Providers

Only now introduce:

```text
LLM
Image
Video
TTS
LipSync
Music
SFX
Upscale
Interpolation
```

through provider/model adapters.

### Stage 8 — Publishing

Implement one real platform adapter end-to-end, then expand.

### Stage 9 — Analytics/Learning

Add analytics collection and later optimization/learning.

---

## 22. What Must NOT Be Done

Do not:

- add Wan directly into Android;
- add ComfyUI calls directly to Compose screens;
- make FFmpeg a UI dependency;
- keep generation state only in `MutableStateFlow` or in-memory objects;
- create a second competing database schema without migrations;
- silently convert network errors into successful production operations;
- mark jobs complete based on simulated progress alone;
- add many platform adapters before the common publishing contract works;
- add dozens of AI providers before the model registry exists;
- perform a massive file move without dependency analysis;
- delete the current MVP before the replacement path has tests.

---

## 23. Baseline Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Android remains the orchestration engine | Critical | Move workflow to backend/job engine |
| Schema divergence | Critical | Implement canonical contracts + migrations |
| Fake job completion | Critical | Mock worker + asset + QC gate |
| Duplicate jobs | High | Idempotency + unique constraints |
| Lost jobs after crash | High | Persistent queue + leases |
| Provider lock-in | High | Provider/model adapter interfaces |
| Asset corruption | High | Hash/integrity validation |
| Cross-project data leakage | Critical | Project-scoped queries/RLS/authorization |
| Publishing duplicates | High | Idempotent publication + remote reconciliation |
| Unverifiable output | High | Render/QC/publish verification |
| Secrets leakage | Critical | Credential boundary + redaction |
| Endless refactor | Medium | Small P0 commits + tests after every step |

---

## 24. Baseline Acceptance Criteria

This audit is considered complete when the following facts are recorded:

- [x] repository tree inspected;
- [x] Android source structure inspected;
- [x] Room layer inspected;
- [x] repository layer inspected;
- [x] network layer inspected;
- [x] ViewModel/UI boundary inspected;
- [x] build configuration inspected;
- [x] current test structure inspected;
- [x] backend existence checked;
- [x] target architecture compared against current implementation;
- [x] P0/P1/P2 gaps identified;
- [x] implementation order established.

The next engineering task is **not** a UI feature. It is **P0 Foundation: canonical contracts + backend skeleton + domain boundaries**, implemented incrementally with tests.

---

## 25. Audit Conclusion

The project has a valid MVP starting point, but it should currently be classified as:

> **Prototype / Early MVP — not production-ready AI Content Factory.**

The existing Android application should be preserved as the initial control-plane shell while the production architecture is built around it.

The safest strategy is evolutionary rather than destructive:

```text
Current Android MVP
       ↓
Contract Foundation
       ↓
Backend + Persistence
       ↓
Job Engine + Queue
       ↓
Deterministic Mock Pipeline
       ↓
Assets + QC
       ↓
Timeline + Renderer
       ↓
Real AI Providers
       ↓
Publishing
       ↓
Analytics + Learning
```

This order minimizes rework, prevents provider-specific architecture from contaminating the core, and creates a testable Golden E2E path before introducing expensive GPU workloads.
