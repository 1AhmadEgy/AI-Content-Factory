# WORKER_PROVIDER_ARCHITECTURE.md

**Version:** 1.0  
**Status:** Normative engineering specification  
**Scope:** Workers, providers, model adapters, queue execution, resources, AI/media backends

---

## 1. Purpose

This document defines the execution architecture for AI Content Factory. It is the contract between the Job Engine and every execution backend, including local models, ComfyUI, HTTP services, CLI processes, FFmpeg, GPU workers, and future providers.

The central rule is:

> The application schedules capabilities and jobs; workers execute them; providers/models are replaceable implementations.

No feature may depend directly on a specific AI vendor, model name, GPU machine, or media executable.

This document complements:

- `PROJECT_RULES.md`
- `DEVELOPER_IMPLEMENTATION_GUIDE.md`
- `CONTRACTS_SPECIFICATION.md`
- `DATABASE_SCHEMA_SPECIFICATION.md`
- `API_SPECIFICATION.md`

If an implementation conflicts with these documents, the documented contract wins unless the contract is deliberately versioned.

---

## 2. Architectural Boundary

```text
Android / Web UI
       |
       v
     API
       |
       v
 Orchestrator / Job Engine
       |
       v
 Queue + Scheduler
       |
       +-----------------------------+
       |                             |
       v                             v
 Worker Runtime                 Resource Manager
       |
       +---------+---------+---------+---------+
       |         |         |         |         |
      LLM      Image     Video      TTS      Media
       |         |         |         |         |
       +---------+---------+---------+---------+
                         |
                    Provider Adapter
                         |
          +--------------+---------------+
          |              |               |
       ComfyUI       Local Model       HTTP/CLI
          |              |               |
          +--------------+---------------+
                         |
                       Assets
                         |
                         v
                    QC / Timeline
                         |
                         v
                      Render
```

### Hard boundary

Android must never directly control GPU processes, ComfyUI, FFmpeg, model servers, or provider secrets.

Backend/orchestration may submit and monitor jobs. Heavy computation belongs to dedicated workers or explicitly configured local/cloud execution nodes.

---

## 3. Core Abstractions

The system MUST expose stable interfaces for these concepts:

1. `Worker`
2. `Provider`
3. `ModelAdapter`
4. `JobExecutor`
5. `ResourceManager`
6. `Queue`
7. `ArtifactStore`
8. `CapabilityRegistry`
9. `HealthMonitor`
10. `CancellationController`

Implementations may use any programming language, framework, or runtime.

### 3.1 Worker

A worker is an execution process that receives jobs and produces artifacts.

```text
Worker
- initialize()
- healthCheck()
- capabilities()
- execute(job)
- cancel(job)
- shutdown()
```

Worker requirements:

- advertise capabilities before accepting jobs;
- reject unsupported job types;
- enforce resource requirements;
- emit progress;
- preserve job and provider correlation IDs;
- support cancellation where technically possible;
- never report COMPLETED without validated outputs;
- release resources after success, failure, or cancellation;
- avoid leaking secrets in logs.

### 3.2 Provider

A provider is an implementation endpoint capable of performing one or more generation operations.

```text
Provider
- id()
- healthCheck()
- capabilities()
- models()
- execute(request)
- cancel(providerRunId)
```

Examples include:

- ComfyUI
- local LLM runtime
- local image/video model server
- TTS server
- lip-sync service
- HTTP API
- CLI process

The rest of the system must not need to know which provider implementation was selected.

### 3.3 ModelAdapter

A `ModelAdapter` translates the canonical job contract into a model/provider-specific request.

```text
ModelAdapter
- modelId()
- validate(input)
- buildRequest(input, context)
- parseResponse(response)
- estimateResources(input)
```

This prevents model-specific parameters from contaminating Domain and UI code.

### 3.4 JobExecutor

`JobExecutor` coordinates one canonical job from validation to output registration.

```text
JobExecutor
- validate(job)
- resolveModel(job)
- reserveResources(job)
- createProviderRun(job)
- executeProviderRun(job)
- collectArtifacts(job)
- runRequiredQC(job)
- finalize(job)
```

It owns orchestration, not model internals.

---

## 4. Worker Types

The reference worker categories are:

| Worker | Job types | Typical runtime |
|---|---|---|
| LLM Worker | story, character, scene, metadata | local LLM / HTTP |
| Image Worker | character/world/shot images | ComfyUI / local model |
| Video Worker | shot/video generation | ComfyUI / local video model |
| TTS Worker | dialogue voice | local TTS / HTTP |
| LipSync Worker | audio-video synchronization | local model / service |
| Music Worker | background music | local model / service |
| SFX Worker | sound effects | local model / service |
| Upscale Worker | image/video upscale | local GPU tool |
| Interpolation Worker | frame interpolation | local GPU tool |
| Render Worker | timeline/render/subtitles | FFmpeg / renderer |

A worker may implement multiple categories, but capability boundaries must remain explicit.

---

## 5. Provider-Agnostic Design

### Forbidden

```text
SceneGenerator -> ComfyUI directly
VideoGenerator -> Wan directly
VoiceGenerator -> ProviderX directly
Android -> FFmpeg
```

### Required

```text
SceneGenerationJob
       |
       v
JobExecutor
       |
       v
ModelRouter
       |
       v
ModelAdapter
       |
       v
Provider
       |
       v
Execution backend
```

This allows a model or provider to be replaced without rewriting the application.

---

## 6. Capability Model

Every worker/provider must advertise capabilities.

Minimum capability fields:

```text
capabilityId
category
jobTypes
modelIds
inputTypes
outputTypes
maxResolution
maxDuration
supportsBatch
supportsStreaming
supportsCancellation
supportsProgress
resourceRequirements
licenseStatus
availability
```

Capability discovery must be dynamic where practical.

A job should be rejected early if no available worker can satisfy its capability requirements.

---

## 7. Model Registry Integration

The Model Registry is authoritative for model metadata.

Minimum model record:

```text
id
name
version
category
provider
runtime
capabilities
hardwareRequirements
license
quality
speed
enabled
```

Workers MUST NOT invent license status locally when a registry record exists.

Allowed license states:

- `VERIFIED`
- `UNKNOWN`
- `RESTRICTED`
- `BLOCKED`

`UNKNOWN` is not equivalent to safe/approved.

A `BLOCKED` model must never execute. `RESTRICTED` requires policy validation before execution.

---

## 8. Model Router

The Model Router selects an executable model/provider based on requirements rather than hard-coded names.

Selection inputs may include:

- job type;
- quality target;
- resolution;
- duration;
- style/capability requirements;
- hardware availability;
- VRAM/RAM/CPU requirements;
- latency priority;
- batch requirements;
- license policy;
- user/project preferences;
- provider health;
- historical success rate.

A deterministic selection policy should be used initially:

```text
1. validate capability
2. validate license
3. validate hardware
4. validate provider health
5. apply project/model preference
6. rank quality/speed/resource cost
7. select highest valid candidate
```

Later versions may add adaptive routing based on measured quality and reliability.

---

## 9. Supported Provider Adapters

### 9.1 ComfyUI Adapter

ComfyUI must be integrated through an adapter.

Responsibilities:

- discover/check ComfyUI availability;
- submit workflow payload;
- map canonical inputs to workflow inputs;
- track execution/progress;
- retrieve generated files;
- normalize artifacts;
- support cancellation when available;
- preserve workflow/model provenance.

The application must not embed ComfyUI workflow JSON throughout business logic.

Recommended structure:

```text
providers/comfyui/
  ComfyUiProvider
  ComfyUiClient
  ComfyUiWorkflowAdapter
  ComfyUiMapper
  ComfyUiHealthCheck
```

Workflows should be versioned and treated as provider-specific assets/configuration.

### 9.2 Local Model Adapter

For models running directly on a local machine:

```text
LocalModelProvider
  -> process/server manager
  -> model adapter
  -> artifact collector
```

It must enforce timeouts, process isolation, resource limits where possible, and cleanup.

### 9.3 HTTP Provider Adapter

For HTTP services:

- timeout every request;
- support retries only for retryable errors;
- use request correlation IDs;
- never log Authorization headers;
- normalize provider errors into canonical error codes;
- persist provider request/response metadata needed for provenance, excluding secrets.

### 9.4 CLI Process Adapter

For FFmpeg or other command-line tools:

- use argument arrays rather than unsafe shell concatenation;
- validate input/output paths;
- capture exit code and stderr safely;
- enforce timeout/cancellation;
- report progress when parsable;
- verify output files after process completion.

---

## 10. Video Generation Architecture

Video generation is a capability, not a model name.

The system may eventually support different local video models and workflows, including Wan-family implementations, but no core contract may require a specific model.

Canonical input should contain concepts such as:

```text
prompt
negativePrompt
referenceAssetIds
characterIds
worldId
sceneId
shotId
duration
fps
resolution
aspectRatio
seed
motionStrength
styleConstraints
consistencyConstraints
```

Provider-specific fields belong inside an adapter/provider extension object, not the shared domain contract.

Video output must become an Asset with:

- MIME type;
- dimensions;
- duration;
- frame rate;
- hash;
- provider;
- model/version;
- seed if available;
- source assets;
- job ID;
- provenance;
- QC result.

---

## 11. LLM Architecture

LLM execution must support both local and remote implementations.

Canonical operations include:

- story generation;
- story revision;
- character generation;
- world generation;
- scene generation;
- shot planning;
- dialogue generation;
- metadata generation.

The LLM adapter must normalize:

- text output;
- structured JSON output;
- token/usage metadata where available;
- model/version;
- deterministic seed/settings where supported;
- safety/validation errors.

Structured generation must be schema-validated before domain persistence.

---

## 12. TTS Architecture

TTS workers accept canonical dialogue/voice requests.

Inputs may include:

```text
text
language
voiceId
speakerId
emotion
speed
pitch
style
seed
```

Outputs must be registered as audio Assets with duration, sample rate, channels, format, and provenance.

The system should support voice profiles independent of a particular TTS engine.

---

## 13. LipSync Architecture

Lip-sync execution accepts at minimum:

```text
videoAssetId
voiceAssetId
characterId
faceRegionHints?
qualityProfile?
```

The worker must verify that source assets exist and are compatible before execution.

Output is a new derived video Asset. The original source assets must remain immutable.

---

## 14. Music and SFX

Music and SFX use the same provider abstraction as other AI categories.

Music inputs may include:

- duration;
- mood;
- genre/style;
- tempo;
- instrumentation;
- scene context;
- loopability.

SFX inputs may include:

- event description;
- duration;
- intensity;
- environment;
- timing context.

All generated audio must carry provenance and license metadata.

---

## 15. Upscaling and Interpolation

Upscale and interpolation are post-processing capabilities.

They must operate on immutable input Assets and create new output Assets.

Examples:

```text
video -> upscale -> video'
video -> interpolation -> video'
image -> upscale -> image'
```

The system must not silently replace the source asset.

---

## 16. Render Worker / FFmpeg

Rendering is separate from generation.

The Render Worker receives a canonical Timeline and Render specification.

FFmpeg is an implementation detail behind the renderer abstraction.

```text
RenderService
   |
   +-- FfmpegRenderer
   +-- FutureRenderer
```

Default target may be:

```text
Container: MP4
Video: H.264
Audio: AAC
Aspect: 9:16
Resolution: 1080x1920
```

These are defaults, not immutable requirements.

The renderer must verify:

- all referenced Assets exist;
- timeline has no invalid overlaps where prohibited;
- output path is writable;
- output is readable after rendering;
- duration is non-zero and within expected bounds;
- media probe succeeds.

---

## 17. Resource Manager

Heavy jobs require resource reservation.

Tracked resources should include:

```text
CPU cores
RAM
GPU
VRAM
storage
network
concurrency slots
process slots
```

A resource request may look conceptually like:

```text
ResourceRequest
  cpuCores
  ramMb
  gpuId?
  vramMb
  diskMb
  estimatedDuration
  exclusiveGpu
```

A worker must not begin a resource-intensive job until required resources are reserved.

Resources must be released on every terminal path.

---

## 18. Hardware Detection

Workers should report hardware capabilities where available:

- CPU model/count;
- system RAM;
- GPU vendor/model;
- VRAM;
- accelerator availability;
- storage capacity;
- runtime versions.

Hardware detection must be advisory and refreshed periodically.

A failed hardware probe must not crash the entire orchestration service.

---

## 19. Queue and Scheduler

The Queue is the boundary between job creation and execution.

Minimum queue features:

- priority;
- FIFO ordering within priority where appropriate;
- dependency awareness;
- concurrency limits;
- resource-aware scheduling;
- retry scheduling;
- cancellation;
- stale-job recovery;
- idempotency/deduplication.

Suggested priority levels:

```text
CRITICAL
HIGH
NORMAL
LOW
BACKGROUND
```

The scheduler must avoid starvation of lower priorities through configurable fairness rules.

---

## 20. Job Dependencies

Jobs may depend on other jobs.

Example:

```text
Story
  -> Character
  -> World
  -> Scene
  -> Shot
  -> Image
  -> Video
  -> TTS
  -> LipSync
  -> QC
  -> Best Take
  -> Timeline
  -> Render
```

A dependent job must not execute until all required dependencies are successful.

If an upstream job fails permanently, dependents should become blocked or failed with an explicit dependency error rather than running with missing inputs.

---

## 21. Idempotency and Deduplication

Job execution must be safe against duplicate delivery.

Canonical deduplication identity should include, as appropriate:

```text
projectId
jobType
targetId
normalizedInputHash
modelId
providerPolicy
```

Do not deduplicate jobs merely because their prompts are identical if their referenced assets, seed, target, or generation policy differ.

Provider submission should also use an idempotency key when supported.

---

## 22. Retry Policy

Retries are permitted only for retryable failures.

Typical retryable cases:

- temporary provider unavailable;
- network timeout;
- transient worker overload;
- temporary resource exhaustion;
- provider 5xx-type failure.

Typical non-retryable cases:

- invalid input;
- missing asset;
- blocked license;
- unsupported model capability;
- corrupted source;
- permanent validation failure.

Use bounded retries with exponential backoff and jitter.

A retry must increment the attempt count and preserve the failure history.

---

## 23. Provider Failover

Fallback to another provider/model is allowed only when policy permits it.

Failover must not silently change user-visible requirements.

Example:

```text
Preferred Video Model
      |
   unavailable
      v
Compatible Local Video Model
      |
   unavailable
      v
Another Approved Provider
```

The selected fallback must satisfy minimum capability and license constraints.

Provider changes must be recorded in provenance.

---

## 24. Cancellation

Cancellation is cooperative where possible.

Flow:

```text
API cancel
 -> Job Engine marks cancellation requested
 -> Queue removes if not started
 -> Worker receives cancellation
 -> Provider cancellation attempted
 -> process cleanup
 -> final CANCELLED state
```

A job already producing an irreversible provider-side operation may require a cancellation-pending state internally.

Cancellation must never be falsely reported as successful merely because a request was sent.

---

## 25. Progress Reporting

Progress should be normalized to `0..100`.

Progress sources may include:

- provider progress;
- workflow node progress;
- estimated local process progress;
- phase-weighted orchestration progress.

Unknown progress is valid. Do not fabricate precise percentages when the backend provides no reliable progress signal.

Events should include:

```text
jobId
providerRunId?
phase?
progress?
timestamp
sequence/version
message?
```

Consumers must tolerate duplicate and out-of-order events.

---

## 26. Health Checks

Three levels are recommended:

### Liveness
Process is alive.

### Readiness
Worker is initialized and can accept jobs.

### Capability health
Specific provider/model capability is currently usable.

A worker may be alive while a specific model is unavailable.

Health status should therefore be capability-specific where possible.

---

## 27. Timeouts

Every external operation must have a timeout policy.

Timeout categories may include:

- connection timeout;
- request timeout;
- provider execution timeout;
- artifact download timeout;
- render timeout;
- idle timeout.

Timeouts must map to canonical `TIMEOUT` or a more specific retryable provider/resource error.

---

## 28. Artifact Contract

Workers must never return an opaque file path as the only output.

They must register an Asset containing at minimum:

```text
assetId
type
path/storageKey
mime
size
hash
metadata
provider
model
sourceAssetIds
jobId
createdAt
```

Generation metadata should include prompt/negative prompt/seed when applicable.

Artifacts should be immutable after registration. Corrections create new derived Assets.

---

## 29. Provenance

Every generated or transformed Asset must be traceable.

Minimum provenance chain:

```text
Asset
  -> Job
  -> ProviderRun
  -> Provider
  -> Model/version
  -> Input Assets
  -> Parameters
  -> Timestamp
```

This is required for reproducibility, debugging, licensing review, and quality analysis.

---

## 30. Security

Secrets may exist only in approved secret/configuration systems.

Never store or log:

- API keys;
- access tokens;
- passwords;
- private credentials;
- signed private URLs unless explicitly safe and short-lived.

Provider adapters must receive credentials through dependency injection/configuration, not hard-coded constants.

Worker logs must redact sensitive headers and values.

---

## 31. Replit and Local/GPU Boundary

Replit is suitable for:

- backend/API development;
- orchestration;
- database integration;
- queue development;
- contract tests;
- mock workers;
- lightweight services.

Heavy GPU workloads should remain on:

- a local GPU machine;
- a dedicated GPU server;
- a compatible self-hosted runtime;
- or an explicitly configured external provider.

The backend must communicate with such workers through stable worker/provider contracts.

This separation allows the project to remain usable in a lightweight development environment while supporting powerful local hardware in production.

---

## 32. Mock Workers

Mock mode is mandatory for deterministic CI and development.

Mock workers must:

- require no GPU;
- require no external API;
- produce deterministic outputs from deterministic inputs;
- simulate progress;
- support success/failure/cancellation scenarios;
- create valid test Assets;
- exercise the real Job Engine and contracts.

The mock path must not bypass orchestration logic.

---

## 33. Observability

Every execution should be traceable using:

```text
requestId
projectId
jobId
providerRunId
workerId
modelId
attempt
```

Metrics should include:

- queue latency;
- execution latency;
- success/failure rate;
- retry count;
- provider availability;
- resource utilization;
- output validation failures;
- QC failure rate;
- cancellation rate.

Logs must be structured where possible.

---

## 34. Error Normalization

Provider-specific errors must be converted to canonical errors.

Examples:

```text
provider HTTP 503 -> PROVIDER_UNAVAILABLE
missing model -> MODEL_UNAVAILABLE
insufficient VRAM -> RESOURCE_UNAVAILABLE / GPU_UNAVAILABLE
invalid request -> VALIDATION_ERROR
blocked model -> MODEL_LICENSE_BLOCKED
render exit failure -> RENDER_FAILED
missing output -> ASSET_NOT_FOUND / INTERNAL_ERROR
```

Provider-specific diagnostic information may remain in a non-sensitive `details` field.

---

## 35. Execution State Machine

```text
PENDING
  -> QUEUED
  -> RUNNING
  -> COMPLETED

RUNNING
  -> RETRYING -> QUEUED
  -> FAILED
  -> CANCELLED
  -> PAUSED

PAUSED
  -> QUEUED
  -> CANCELLED
```

State transitions must be validated centrally.

A worker must not directly mutate arbitrary job state outside the Job Engine contract.

---

## 36. Worker Registration

Workers should register:

```text
workerId
name
version
runtime
host
status
capabilities
resources
lastHeartbeat
```

Heartbeats prevent scheduling work to dead workers.

Stale workers must eventually be marked unavailable and their running jobs reconciled.

---

## 37. Orphan and Crash Recovery

If a worker disappears while a job is RUNNING:

1. detect stale heartbeat;
2. identify affected jobs;
3. determine whether provider execution may still exist;
4. reconcile provider status if possible;
5. avoid duplicate expensive execution when status is unknown;
6. retry or fail according to policy;
7. preserve the incident in job events/audit data.

Never assume worker death means provider execution definitely stopped.

---

## 38. Concurrency

Concurrency must be controlled at multiple levels:

```text
Global
 -> Worker
   -> GPU
     -> Provider
       -> Model
```

For example, a 12 GB GPU may allow one large video job but several small image jobs. Resource profiles should drive scheduling rather than arbitrary thread counts.

---

## 39. Batch Execution

Workers may support batch execution where beneficial.

Batching must not change canonical job semantics.

Each logical job retains its own ID and output Assets, even when physically processed in a shared provider batch.

---

## 40. Quality Gate

Generation completion is not the same as production completion.

Required pattern:

```text
Provider success
      |
      v
Artifact validation
      |
      v
Technical QC
      |
      v
Media/continuity/semantic QC
      |
      +---- fail -> retry/regenerate/review
      |
      v
Approved Asset
```

A provider reporting success cannot bypass QC requirements.

---

## 41. Testing Strategy

Every adapter should have:

1. unit tests;
2. contract tests;
3. failure-path tests;
4. cancellation tests;
5. timeout tests;
6. artifact validation tests;
7. provenance tests;
8. license-policy tests.

Integration tests should run against real providers only when explicitly enabled.

CI must use Mock Workers by default.

---

## 42. Golden Worker Test

The minimum end-to-end worker test is:

```text
Create Project
 -> create Story
 -> create Character
 -> create World
 -> create Scene
 -> create Shot
 -> enqueue Image Job
 -> Mock Image Worker
 -> Asset created
 -> QC
 -> approve
```

The full production golden path extends this through:

```text
Video -> TTS -> LipSync -> Music/SFX -> Timeline -> Render
```

No stage may rely on a fake in-memory shortcut that bypasses the actual contracts.

---

## 43. Provider Contract Test Matrix

For each provider adapter test:

| Scenario | Expected result |
|---|---|
| healthy provider | READY |
| unavailable provider | PROVIDER_UNAVAILABLE |
| unsupported capability | MODEL_UNAVAILABLE / validation failure |
| invalid input | VALIDATION_ERROR |
| timeout | TIMEOUT |
| temporary failure | retryable failure |
| permanent failure | FAILED |
| cancellation | CANCELLED or documented pending state |
| valid artifact | Asset registered |
| corrupt artifact | ASSET_CORRUPTED |
| blocked license | MODEL_LICENSE_BLOCKED |
| duplicate submission | idempotent result |

---

## 44. Implementation Package Boundary

Recommended implementation structure:

```text
backend/
  workers/
    core/
    llm/
    image/
    video/
    tts/
    lipsync/
    music/
    sfx/
    upscale/
    interpolation/
    render/

  providers/
    core/
    comfyui/
    local/
    http/
    cli/

  orchestration/
    scheduler/
    queue/
    routing/
    resources/
    retry/
    recovery/
```

Actual repository structure must be adapted to the existing codebase after inspection. Do not mass-move files merely to match this diagram.

---

## 45. Implementation Order

### Phase W0 — Inventory

- inspect existing workers/providers;
- identify current execution paths;
- identify direct provider coupling;
- identify current FFmpeg/ComfyUI/model integrations;
- identify existing queue/job state.

### Phase W1 — Core Contracts

Implement stable interfaces for Worker, Provider, ModelAdapter, JobExecutor, ResourceManager, Queue, and ArtifactStore.

### Phase W2 — Job Execution

Connect contracts to the existing Job Engine with lifecycle validation, progress, cancellation, retries, and idempotency.

### Phase W3 — Mock Runtime

Implement deterministic Mock Workers and Golden E2E execution.

### Phase W4 — Provider Adapters

Add HTTP, CLI, local runtime, and ComfyUI adapters behind the provider contract.

### Phase W5 — Model Registry/Router

Connect model capabilities, hardware requirements, license policy, and routing.

### Phase W6 — Resource Management

Add GPU/VRAM/CPU/RAM/storage detection and scheduling.

### Phase W7 — Media Pipeline

Add TTS, image, video, lip-sync, music, SFX, upscale, interpolation, and render workers as capabilities.

### Phase W8 — QC/Provenance

Enforce output validation, provenance, continuity, and quality gates.

### Phase W9 — Production Hardening

Add recovery, observability, load tests, security review, documentation, and release gates.

---

## 46. Non-Negotiable Rules

1. No UI-to-provider direct calls.
2. No provider-specific logic in Domain models.
3. No hard-coded dependency on a single AI model.
4. No model execution without capability validation.
5. No blocked-license model execution.
6. Unknown license is not automatically safe.
7. No completed job without validated output.
8. No artifact without provenance.
9. No unbounded retries.
10. No secrets in source control or logs.
11. No heavy GPU workload requirement for CI.
12. Mock mode must exercise real orchestration.
13. Source Assets remain immutable.
14. Provider changes must be observable and recorded.
15. Worker crashes must be recoverable.
16. Resource reservations must always be released.
17. External operations must have timeouts.
18. Canonical contracts must not be polluted by provider-specific fields.
19. FFmpeg is a renderer implementation, not a Domain dependency.
20. ComfyUI is a provider/runtime integration, not a Domain dependency.

---

## 47. Definition of Done

Worker/provider architecture is considered complete only when:

- [ ] interfaces are implemented and documented;
- [ ] existing direct integrations are mapped;
- [ ] job lifecycle is centrally enforced;
- [ ] capability discovery works;
- [ ] model routing works;
- [ ] resource requirements are respected;
- [ ] retries are bounded and classified;
- [ ] cancellation is implemented or explicitly documented per provider;
- [ ] artifacts are validated;
- [ ] provenance is persisted;
- [ ] license policy is enforced;
- [ ] Mock Workers run in CI;
- [ ] Golden E2E passes;
- [ ] provider contract tests pass;
- [ ] worker crash recovery is tested;
- [ ] no secrets are logged;
- [ ] observability fields are present;
- [ ] documentation matches implementation;
- [ ] existing tests/build remain green.

---

## 48. Developer Execution Rule

For every worker/provider task:

```text
READ
  -> inspect existing implementation
UNDERSTAND
  -> identify current contracts and dependencies
PLAN
  -> define smallest safe change
IMPLEMENT
  -> preserve public contracts
TEST
  -> unit + contract + failure paths
BUILD
  -> verify repository build
REVIEW
  -> inspect coupling, security, retries, resources
DOCUMENT
  -> update relevant specification
```

Do not replace a working provider with a new framework merely for architectural aesthetics.

Refactor incrementally, preserve behavior, and introduce abstractions around verified boundaries.

---

## 49. Final Reference Pipeline

```text
User Request
    |
    v
API
    |
    v
Job Engine
    |
    v
Validation
    |
    v
Dependency Resolver
    |
    v
Model Router
    |
    +---- Model Registry
    +---- License Policy
    +---- Capability Registry
    +---- Resource Manager
    |
    v
Queue / Scheduler
    |
    v
Worker
    |
    v
Provider Adapter
    |
    v
Model / Runtime / Tool
    |
    v
Artifact Collector
    |
    v
Asset + Provenance
    |
    v
QC
    |
    +---- regenerate/retry/review
    |
    v
Approved Asset
    |
    v
Timeline
    |
    v
Render Worker
    |
    v
Final Output
```

This architecture is intentionally provider-neutral so AI Content Factory can evolve from lightweight local development to multi-GPU, self-hosted, or optional external execution without rewriting the product core.
