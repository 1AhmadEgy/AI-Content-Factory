# AI Model Registry Specification

**Version:** 1.0  
**Status:** Normative Engineering Specification  
**Scope:** AI-Content-Factory

## 1. Purpose

The Model Registry is the single source of truth for every AI model/runtime that can participate in the production pipeline. It separates product logic from individual models, providers, runtimes, GPU machines, and deployment methods.

The system MUST be able to add, remove, upgrade, disable, or replace a model without changing Story, Scene, Shot, Job, Timeline, or UI domain logic.

The registry covers LLM, image, video, TTS, lip-sync, music, SFX, upscaling, interpolation, embeddings/vision where required, and future model categories.

## 2. Architectural Position

```text
UI
 ↓
UseCase
 ↓
Repository / API
 ↓
Generation Job
 ↓
Orchestrator
 ↓
Model Router
 ↓
Model Registry ─── Capability / License / Resource checks
 ↓
Provider Adapter / Runtime Adapter
 ↓
Worker
 ↓
Model Runtime
 ↓
Artifacts + Provenance + QC
```

The registry is metadata and policy. It MUST NOT become the execution engine.

## 3. Core Principles

1. Model-agnostic domain logic.
2. Provider-agnostic job contracts.
3. Explicit capability declarations.
4. Explicit hardware/resource requirements.
5. Explicit license status.
6. Versioned model identities.
7. Deterministic routing when possible.
8. Safe fallback only when capability and policy requirements remain satisfied.
9. No silent substitution of models.
10. Every generated asset records the exact model and version used.
11. Disabled, unavailable, incompatible, or license-blocked models MUST never be selected.
12. Unknown license status is not equivalent to verified permission.

## 4. Model Identity

Every model MUST have a stable registry ID and immutable version identity.

Minimum fields:

```text
id
name
version
family
category
provider
runtime
status
capabilities
inputSchema
outputSchema
resourceRequirements
license
qualityProfile
performanceProfile
configuration
endpoint
createdAt
updatedAt
```

Recommended identity:

```text
modelId = <provider>:<family>:<version>:<runtime>
```

The implementation may use another opaque ID, but model identity MUST remain stable and unambiguous.

## 5. Model Categories

```text
LLM
VISION_LLM
EMBEDDING
IMAGE
VIDEO
TTS
LIPSYNC
MUSIC
SFX
UPSCALE
INTERPOLATION
TRANSCRIPTION
VISION_ANALYSIS
RENDER_AUXILIARY
```

New categories MUST be additive and versioned rather than changing the meaning of an existing category.

## 6. Model Status

```text
REGISTERED
ENABLED
DISABLED
DEPRECATED
UNAVAILABLE
LICENSE_BLOCKED
INCOMPATIBLE
```

Rules:

- `REGISTERED`: known to the system but not necessarily routable.
- `ENABLED`: eligible for routing if all runtime/resource/license checks pass.
- `DISABLED`: explicitly excluded by configuration.
- `DEPRECATED`: existing jobs may remain reproducible; new jobs should normally avoid it.
- `UNAVAILABLE`: runtime/provider cannot currently serve it.
- `LICENSE_BLOCKED`: policy prevents execution.
- `INCOMPATIBLE`: current environment cannot satisfy requirements.

## 7. Capability Model

Capabilities MUST be machine-readable.

Examples:

```text
text_generation
structured_json
long_context
image_generation
image_editing
character_consistency
reference_image
text_to_video
image_to_video
video_to_video
camera_control
motion_control
speech_synthesis
voice_cloning
multilingual_tts
lip_sync
music_generation
sfx_generation
upscaling
frame_interpolation
```

A Job MUST request capabilities, not a hard-coded model name, unless the user explicitly pins a model.

## 8. Capability Constraints

Each capability can declare constraints such as:

```text
minResolution
maxResolution
supportedAspectRatios
maxDurationSeconds
supportedLanguages
supportedInputMimeTypes
supportedOutputMimeTypes
maxReferenceImages
requiresReferenceImage
supportsSeed
supportsNegativePrompt
supportsControlInputs
```

The Router MUST reject a candidate that cannot satisfy mandatory constraints.

## 9. Resource Requirements

Models MUST declare resource requirements when known.

```text
cpuCoresMin
ramGbMin
vramGbMin
storageGbMin
gpuVendor
gpuArchitecture
cudaVersion
rocmVersion
computeCapability
precision
quantization
estimatedVramGb
estimatedRuntimeSeconds
concurrencyLimit
```

Requirements can be hard or soft:

```text
HARD: execution is impossible without it.
SOFT: execution is possible but degraded.
```

The Resource Manager is authoritative for current availability; the Registry is authoritative for declared requirements.

## 10. Runtime Types

Supported runtime abstractions SHOULD include:

```text
COMFYUI
PYTORCH
DIFFUSERS
TRANSFORMERS
OLLAMA
VLLM
ONNX
TENSORRT
HTTP
GRPC
CLI
CUSTOM
```

The runtime name describes how the model is executed, not what provider owns it.

## 11. Provider Model

A provider is an execution source. A model is a capability-bearing artifact.

Examples:

```text
LocalComfyUIProvider
LocalDiffusersProvider
LocalLLMProvider
OllamaProvider
VllmProvider
HttpProvider
CliProvider
```

A provider MUST NOT expose provider-specific behavior through the core domain contract.

## 12. Model Adapter

Conceptual interface:

```text
ModelAdapter {
    describe(): ModelDescriptor
    validate(input): ValidationResult
    estimateResources(input): ResourceEstimate
    execute(context, input): ModelExecutionResult
    cancel(executionId): CancellationResult
    healthCheck(): HealthStatus
}
```

The concrete implementation may be language-specific, but the semantic contract MUST remain equivalent.

## 13. Model Registry API

Minimum operations:

```text
register(model)
get(modelId, version)
list(filters)
updateMetadata(modelId, version)
enable(modelId, version)
disable(modelId, version)
deprecate(modelId, version)
resolve(capabilityRequest)
validate(modelId, version)
```

Mutation operations MUST be audited.

## 14. Model Router

The Router converts a job requirement into an ordered set of eligible model candidates.

Input:

```text
category
requiredCapabilities
qualityTarget
speedTarget
resourceBudget
licensePolicy
preferredProvider
preferredModel
seed/determinism requirements
language
resolution
aspectRatio
duration
reference requirements
```

Output:

```text
primaryCandidate
fallbackCandidates
selectionReasons
rejectedCandidates
policyDecision
```

The Router MUST explain why a model was selected or rejected in debug/observability metadata.

## 15. Routing Priority

Default scoring order:

1. License/policy compliance.
2. Capability compatibility.
3. Hardware/runtime compatibility.
4. Input/output compatibility.
5. User-pinned model/provider, when explicitly requested.
6. Quality target.
7. Reliability/health.
8. Resource availability.
9. Speed.
10. Cost, when cost exists.

A lower-priority factor MUST NOT override a higher-priority safety or compatibility rule.

## 16. Explicit Model Pinning

Users or workflows may pin:

```text
provider
model
version
runtime
```

Pinned execution MUST fail clearly if the requested model cannot run. The system MUST NOT silently replace a pinned model unless the user/workflow explicitly allows fallback.

## 17. Fallback Policy

Fallback is allowed only when:

- The fallback has the required capabilities.
- License policy permits it.
- Input/output contracts remain compatible.
- The workflow permits substitution.
- The substitution is recorded.

Example:

```text
VIDEO_GENERATION
primary: local-model-A
fallback: local-model-B
fallback: remote-provider-C
```

Every fallback MUST generate an observable event and remain visible in provenance.

## 18. License Registry

License metadata MUST include:

```text
licenseName
licenseVersion
source
status
commercialUse
redistribution
modelWeightsAllowed
derivativeUseAllowed
attributionRequired
restrictions
reviewedAt
reviewedBy
```

Status:

```text
VERIFIED
UNKNOWN
RESTRICTED
BLOCKED
```

Routing rules:

- `VERIFIED`: eligible subject to other constraints.
- `UNKNOWN`: not eligible for automatic production routing when the workflow requires verified licensing.
- `RESTRICTED`: eligible only if the current project policy explicitly permits the restriction.
- `BLOCKED`: never eligible.

## 19. Model Versioning

A model version MUST be immutable after publication to the registry.

If weights, architecture, prompt format, runtime compatibility, or significant behavior changes, create a new version.

Existing asset provenance MUST continue pointing to the exact historical version.

## 20. Model Aliases

Aliases such as:

```text
best_free_video
fast_image
local_llm
arabic_tts
```

MAY exist, but aliases are configuration-level selectors, not model identities.

An alias MUST resolve to a concrete model before execution and the resolved identity MUST be stored with the Job and Asset.

## 21. Local Model Discovery

The system MAY discover local runtimes automatically.

Discovery sources include:

```text
ComfyUI API
Ollama API
vLLM API
filesystem/model manifests
Docker services
HTTP health endpoints
CLI inspection
```

Discovered models MUST enter the registry as untrusted metadata until validated.

Discovery MUST NOT automatically mark a model license as VERIFIED.

## 22. ComfyUI Integration

ComfyUI is treated as a runtime/provider adapter, not as the core model abstraction.

The adapter SHOULD:

1. Detect endpoint health.
2. Detect available workflows/models where possible.
3. Map registry capabilities to workflow inputs.
4. Validate required checkpoints/nodes.
5. Submit jobs asynchronously.
6. Track execution progress.
7. Collect resulting artifacts.
8. Record workflow/model provenance.
9. Support cancellation when the runtime permits it.

ComfyUI workflow changes MUST NOT require changes to domain Job contracts.

## 23. Video Model Integration

Video models such as Wan or future alternatives MUST be represented through generic capabilities:

```text
text_to_video
image_to_video
video_to_video
reference_conditioning
camera_control
motion_control
```

The application MUST NOT hard-code `Wan` into the domain layer.

A Wan adapter may live under a provider/runtime integration layer and register one or more concrete model versions.

## 24. LLM Integration

LLM entries SHOULD declare:

```text
contextWindow
structuredOutput
jsonSchemaSupport
toolCalling
vision
streaming
languages
reasoningProfile
```

Both remote APIs and local runtimes MUST implement the same semantic generation contract.

## 25. TTS Integration

TTS models SHOULD declare:

```text
languages
voices
speakingStyles
sampleRate
channels
maxTextLength
voiceCloning
speakerEmbedding
emotionControls
```

Voice identity and model identity are separate concepts.

## 26. LipSync Integration

Lip-sync models SHOULD declare:

```text
inputVideo
inputAudio
faceDetection
multiFace
maxDuration
fpsSupport
resolutionSupport
```

The pipeline MUST preserve source video/audio provenance.

## 27. Music and SFX

Music/SFX models MUST expose generic capabilities such as:

```text
music_generation
loop_generation
stinger_generation
ambient_generation
sound_effect_generation
```

Prompts, seeds, durations, and source assets MUST be recorded.

## 28. Upscaling and Interpolation

These are post-processing model categories.

They MUST declare:

```text
scaleFactors
inputCodecs
outputCodecs
maxResolution
fpsInput
fpsOutput
```

They operate on Asset references and MUST create new derived Assets rather than mutating the original source asset.

## 29. Model Health

Health states:

```text
HEALTHY
DEGRADED
UNAVAILABLE
UNKNOWN
```

Health checks SHOULD verify more than process existence when practical:

- endpoint reachable
- model loaded
- required GPU available
- required dependencies available
- sufficient disk
- test inference/validation where safe

A model may remain registered while being temporarily unavailable.

## 30. Resource-Aware Scheduling

Before execution:

```text
Job → Router → Candidate → ResourceManager.reserve()
```

The reservation MUST account for:

- VRAM
- RAM
- CPU
- GPU occupancy
- disk
- concurrency
- expected duration

If resources cannot be reserved, the job remains queued or selects an eligible alternative.

## 31. Concurrency

Each model/provider may define:

```text
maxConcurrentJobs
maxConcurrentPerGpu
maxQueueDepth
```

The Scheduler MUST prevent overload and avoid allocating two jobs against a resource reservation that cannot support both.

## 32. Determinism

Models SHOULD declare whether they support deterministic execution.

Registry metadata:

```text
supportsSeed
supportsDeterministicMode
determinismLevel
```

CI/mock workflows MUST use deterministic adapters even when production models are nondeterministic.

## 33. Input and Output Schemas

Each model adapter MUST validate its input against the normalized Job Input contract before execution.

The adapter output MUST normalize into:

```text
assetIds
metrics
providerRunId
modelId
modelVersion
warnings
```

Provider-specific response formats MUST remain outside the domain contract.

## 34. Provenance

Every AI-generated Asset MUST preserve at least:

```text
jobId
provider
model
modelVersion
runtime
prompt
negativePrompt
seed
sourceAssetIds
workflowId/workflowVersion when applicable
parameters
createdAt
```

For fallback executions, also record:

```text
requestedModel
selectedModel
fallbackReason
```

## 35. Security

Registry metadata MUST NOT contain raw API keys, passwords, access tokens, or private credentials.

Provider credentials belong in a secure secret/configuration layer.

Logs MUST redact secrets and sensitive request headers.

## 36. Offline / Open-Source Mode

The project SHOULD support a fully local mode where feasible:

```text
Local LLM
Local image model
Local video model
Local TTS
Local lip-sync
Local music/SFX
Local FFmpeg
Local storage
Local queue
```

Remote providers are optional adapters, not architectural requirements.

## 37. Replit Boundary

Replit/backend is suitable for:

- API
- orchestration
- database
- queue control
- registry management
- tests
- mock workers
- lightweight processing

Heavy GPU inference SHOULD run in dedicated GPU workers/local machines or another appropriate execution environment.

The registry MUST make this deployment boundary explicit through runtime/resource metadata.

## 38. Mock Model Registry

CI MUST include deterministic mock models for each core category:

```text
MockLLM
MockImage
MockVideo
MockTTS
MockLipSync
MockMusic
MockSFX
MockUpscale
MockInterpolation
```

Mocks MUST obey the same normalized contracts as production adapters.

## 39. Registry Persistence

Production registry state SHOULD be persisted in the database and versioned through migrations.

Static seed definitions MAY be stored as code/configuration and imported idempotently.

Database records and runtime discovery records MUST be distinguishable.

## 40. Configuration Precedence

Recommended precedence:

```text
Explicit Job Pin
> Workflow Policy
> Project Policy
> Model Alias
> Router Default
> Registry Default
```

Higher-level explicit choices MUST NOT be silently overridden by lower-level defaults.

## 41. Observability

Every routing decision SHOULD emit structured telemetry containing:

```text
jobId
requestedCapabilities
candidateModels
rejectionReasons
selectedModel
selectedRuntime
resourceDecision
licenseDecision
fallbackDecision
```

This information is essential for debugging and quality analysis.

## 42. Metrics

Track at minimum:

```text
jobSuccessRate
jobFailureRate
averageLatency
queueWaitTime
executionTime
retryRate
fallbackRate
resourceUtilization
modelUtilization
providerAvailability
QCFailureRate
```

Metrics MUST distinguish model version and provider where practical.

## 43. Failure Handling

Standard failures map to the contracts defined by `CONTRACTS_SPECIFICATION.md` and `API_SPECIFICATION.md`.

Examples:

```text
MODEL_UNAVAILABLE
MODEL_LICENSE_BLOCKED
RESOURCE_UNAVAILABLE
GPU_UNAVAILABLE
PROVIDER_UNAVAILABLE
TIMEOUT
ASSET_CORRUPTED
```

Do not convert a license or capability failure into a generic retry.

## 44. Retry Rules

Retry only when the failure is plausibly transient.

Examples suitable for retry:

- temporary provider outage
- worker crash
- transient network timeout
- temporary resource contention

Examples normally not suitable for retry:

- invalid input
- unsupported capability
- blocked license
- permanently incompatible hardware
- corrupted workflow definition

Retry policy MUST be bounded and observable.

## 45. Database Relationships

Conceptually:

```text
Model
 ├── ModelVersion
 │    ├── Capabilities
 │    ├── ResourceRequirements
 │    ├── License
 │    ├── ProviderBindings
 │    └── QualityProfile
 │
 └── RuntimeBinding
       └── Worker
```

A GenerationJob references the resolved concrete model version used for execution.

## 46. API Exposure

Public API SHOULD expose safe model metadata:

```text
GET /api/v1/models
GET /api/v1/models/{id}
GET /api/v1/models/{id}/versions
GET /api/v1/capabilities
GET /api/v1/capabilities/{name}
GET /api/v1/workers/capabilities
```

Administrative registry mutations require authorization.

Secrets and internal credentials MUST never be exposed.

## 47. User-Facing Model Selection

UI SHOULD offer meaningful choices such as:

```text
Best Quality
Fastest
Local Only
Free/Open
Low VRAM
High Consistency
Arabic TTS
```

These choices SHOULD resolve to policies/capabilities rather than exposing raw implementation details by default.

Advanced users MAY select exact models and versions.

## 48. Model Evaluation

A model may have evaluation metadata:

```text
qualityScore
consistencyScore
promptAdherenceScore
artifactQualityScore
latencyScore
stabilityScore
```

Evaluation scores are advisory and MUST NOT bypass capability, resource, or license rules.

## 49. Promotion Lifecycle

Recommended lifecycle:

```text
DISCOVERED
→ VALIDATED
→ REGISTERED
→ ENABLED
→ EVALUATED
→ PRODUCTION
→ DEPRECATED
→ RETIRED
```

A model should pass automated validation before production routing.

## 50. Validation Suite

Every registered model SHOULD pass:

1. Metadata validation.
2. Capability validation.
3. Runtime health check.
4. Resource compatibility check.
5. Minimal inference test.
6. Output artifact validation.
7. Provenance validation.
8. License policy validation.
9. Cancellation test where supported.
10. Failure/retry classification test.

## 51. Contract Tests

For every adapter:

```text
Provider Contract Test
Model Adapter Contract Test
Input Validation Test
Output Normalization Test
Health Test
Cancellation Test
Provenance Test
License Test
Resource Test
```

The same suite SHOULD run against mock and production adapters where practical.

## 52. Golden Pipeline Requirement

At minimum, CI MUST prove:

```text
Story
→ Scene
→ Shot
→ GenerationJob
→ Router
→ Mock Model
→ Asset
→ Provenance
→ QC
→ Best Take
→ Timeline
→ Render
```

The pipeline must not depend on an external paid AI provider.

## 53. Non-Negotiable Rules

1. Never hard-code a model into domain logic.
2. Never treat a provider as the model itself.
3. Never hide model substitution.
4. Never execute a license-blocked model.
5. Never treat UNKNOWN license as VERIFIED.
6. Never lose model/version provenance.
7. Never bypass Resource Manager for heavy jobs.
8. Never let UI call a model runtime directly.
9. Never make production state depend solely on in-memory registry data.
10. Never make CI depend on external AI services.
11. Never silently change a pinned model.
12. Never mutate an existing model version's identity.
13. Never store secrets in registry metadata.
14. Never retry permanent validation/license failures.
15. Never couple the core pipeline to ComfyUI, Wan, Ollama, or any other single runtime.

## 54. Implementation Order

### P0 — Foundation
- Model entities/value objects.
- Registry repository.
- Capability definitions.
- License policy.
- Resource requirement schema.
- Contract tests.

### P1 — Routing
- Model Router.
- Candidate scoring.
- Resource filtering.
- License filtering.
- Explicit model pinning.
- Fallback policy.

### P2 — Runtime Adapters
- Mock adapters.
- HTTP adapter.
- CLI adapter.
- ComfyUI adapter.
- Local LLM adapter.
- TTS/lip-sync adapters.

### P3 — Production Infrastructure
- Discovery.
- Worker registration.
- GPU/resource manager.
- Health monitoring.
- Queue integration.
- Provenance persistence.

### P4 — Quality
- Evaluation harness.
- Benchmark datasets.
- Model scoring.
- Automatic promotion/deprecation.
- Regression detection.

## 55. Definition of Done

The Model Registry is considered production-ready only when:

- Models have stable identities and versions.
- Capabilities are machine-readable.
- Resource requirements are enforceable.
- License status is enforceable.
- Router produces explainable decisions.
- Explicit pinning works.
- Fallback is policy-controlled and recorded.
- ComfyUI/local/HTTP/CLI adapters remain isolated.
- Mock models support deterministic CI.
- Provenance is complete.
- Health checks work.
- Retry classification is correct.
- Secrets are isolated.
- Registry state is persisted and migratable.
- Contract tests pass.
- Golden E2E passes without paid external AI.
- Documentation matches implementation.

## 56. Relationship to Other Specifications

This document depends on and must remain consistent with:

- `PROJECT_RULES.md`
- `DEVELOPER_IMPLEMENTATION_GUIDE.md`
- `CONTRACTS_SPECIFICATION.md`
- `DATABASE_SCHEMA_SPECIFICATION.md`
- `API_SPECIFICATION.md`
- `WORKER_PROVIDER_ARCHITECTURE.md`

If a future implementation conflicts with these documents, the conflict MUST be resolved explicitly through a versioned specification change rather than silently diverging in code.

---

**Final rule:** The project owns the pipeline contract. Models, providers, runtimes, and hardware are replaceable implementations behind that contract.