# TIMELINE & RENDERING SPECIFICATION

**Project:** AI Content Factory  
**Document Type:** Normative Engineering Specification  
**Version:** 1.0  
**Status:** Baseline / Implementation Reference

---

## 1. Purpose

This document defines the authoritative architecture and implementation contract for timeline construction, clips, tracks, synchronization, transitions, effects, subtitles, audio mixing, rendering, encoding, export validation, and final-output lifecycle in AI Content Factory.

It complements:

- `PROJECT_RULES.md`
- `DEVELOPER_IMPLEMENTATION_GUIDE.md`
- `CONTRACTS_SPECIFICATION.md`
- `DATABASE_SCHEMA_SPECIFICATION.md`
- `API_SPECIFICATION.md`
- `WORKER_PROVIDER_ARCHITECTURE.md`
- `AI_MODEL_REGISTRY_SPECIFICATION.md`
- `QUEUE_SCHEDULER_SPECIFICATION.md`
- `ASSET_STORAGE_PROVENANCE_SPECIFICATION.md`
- `MEDIA_QC_CONTINUITY_SPECIFICATION.md`

This specification is normative. The renderer MUST produce outputs from explicit, versioned timeline state rather than hidden UI state or arbitrary filesystem paths.

---

# 2. Rendering Philosophy

The factory separates **editorial intent** from **render execution**.

```text
Assets / Best Takes
        ↓
Timeline Model
        ↓
Validation
        ↓
Render Plan
        ↓
Renderer / FFmpeg
        ↓
Staging Output
        ↓
Final QC
        ↓
Immutable Render Asset
```

A timeline is a durable domain object. A render is an execution of that timeline.

A successful render process does not automatically mean the final media is valid.

---

# 3. Core Concepts

The rendering subsystem consists of:

```text
Timeline
Track
Clip
Transition
Effect
Filter
SubtitleTrack
AudioMix
Marker
RenderProfile
RenderPlan
RenderJob
RenderArtifact
```

Responsibilities MUST remain separate.

---

# 4. Timeline Identity

Every timeline MUST have an opaque unique ID.

Recommended fields:

```text
timelineId
projectId
episodeId
version
status
schemaVersion
createdAt
updatedAt
createdBy
```

Optional:

```text
name
description
frameRate
resolution
aspectRatio
sampleRate
colorSpace
renderProfileId
```

Timeline versions SHOULD be immutable once a render has started.

---

# 5. Timeline Status

Recommended states:

```text
DRAFT
VALIDATING
READY
RENDERING
RENDERED
FAILED
ARCHIVED
```

Rules:

- `DRAFT` may be edited.
- `VALIDATING` is being checked for renderability.
- `READY` has passed required timeline validation.
- `RENDERING` has an active render job.
- `RENDERED` has at least one validated render artifact.
- `FAILED` records a failed render attempt without deleting history.
- `ARCHIVED` is retained but not normally edited.

A timeline SHOULD be versioned rather than mutated after production output exists.

---

# 6. Time Representation

Internal timeline time MUST use a precise, deterministic representation.

Recommended:

```text
integer microseconds
```

or another lossless integer timebase.

Do not use floating-point seconds as the canonical persisted representation.

UI may display:

```text
00:01:23.450
```

but persistence should retain exact time values.

---

# 7. Frame Rate

The timeline MUST define an explicit frame rate when video is present.

Examples:

```text
24 fps
25 fps
30 fps
60 fps
```

Fractional rates MUST be represented accurately, for example:

```text
30000/1001
24000/1001
```

Frame calculations MUST avoid accumulated floating-point drift.

---

# 8. Resolution and Aspect Ratio

A render profile MUST define output dimensions.

Examples:

```text
1920x1080  16:9
1080x1920  9:16
1080x1080  1:1
3840x2160  16:9
```

The project default may be configurable; the renderer MUST never assume one universal output size.

Source assets may have different dimensions and must be transformed according to an explicit fit policy.

---

# 9. Fit Policies

Supported conceptual policies:

```text
FIT
FILL
CROP
STRETCH
LETTERBOX
PILLARBOX
SCALE
NONE
```

`STRETCH` SHOULD be disabled by default because it can distort characters and objects.

Crop/fill operations MUST be deterministic.

---

# 10. Track Model

A timeline SHOULD support at least:

```text
VIDEO
DIALOGUE
AUDIO
MUSIC
SFX
SUBTITLE
OVERLAY
EFFECT
```

Each track SHOULD contain:

```text
trackId
timelineId
type
index
name
enabled
muted
locked
clips[]
```

Track ordering MUST be deterministic.

---

# 11. Clip Model

A clip SHOULD contain:

```text
clipId
trackId
assetId
assetVersionId
startTime
duration
sourceIn
sourceOut
speed
volume
opacity
transform
crop
rotation
zIndex
enabled
```

Optional:

```text
blendMode
colorAdjustment
effects[]
transitionIn
transitionOut
metadata
```

A clip MUST reference a logical immutable Asset version, not a raw path.

---

# 12. Source Time Mapping

For a clip:

```text
sourceIn
sourceOut
```

define the source segment.

Playback mapping MUST account for:

```text
speed
reverse when explicitly supported
trim
frame rate conversion
```

The renderer MUST reject invalid mappings such as:

```text
sourceIn < 0
sourceOut <= sourceIn
duration <= 0
```

unless a specific effect contract permits another interpretation.

---

# 13. Clip Overlap

Overlapping clips are legal when the track type supports compositing or mixing.

For example:

```text
Video tracks → compositing
Music tracks → audio mixing
```

For exclusive tracks, illegal overlap MUST be detected during validation.

The renderer MUST NOT silently choose one clip over another unless the track contract explicitly defines that behavior.

---

# 14. Z-Order and Compositing

Video/overlay tracks SHOULD support deterministic layer ordering.

Example:

```text
Background
Character
Foreground
Text/Subtitle
Overlay
```

Z-order must be explicit.

The renderer MUST produce the same layer ordering for identical timeline inputs.

---

# 15. Transform Model

Video clips MAY define:

```text
x
y
scaleX
scaleY
rotation
anchorX
anchorY
```

Transforms SHOULD use a consistent coordinate system.

The coordinate system MUST be documented and shared between editor preview and renderer.

---

# 16. Keyframes

Future/advanced effects MAY support keyframes for:

```text
position
scale
rotation
opacity
volume
filters
```

Keyframes MUST contain deterministic timestamps and interpolation behavior.

Recommended interpolation types:

```text
STEP
LINEAR
EASE_IN
EASE_OUT
EASE_IN_OUT
BEZIER
```

---

# 17. Transitions

The transition system SHOULD support:

```text
CUT
FADE
DISSOLVE
WIPE
SLIDE
CUSTOM
```

A transition has:

```text
transitionId
type
duration
parameters
```

Transition duration MUST NOT exceed the available overlap/source range unless the renderer explicitly supports handle extension.

---

# 18. Handles

When a transition needs frames before/after a clip boundary, the source asset MUST contain sufficient media handles.

If not:

```text
transition validation → ERROR/BLOCKER
```

The renderer MUST NOT silently invent unavailable frames.

---

# 19. Audio Architecture

Audio is first-class timeline data.

The renderer SHOULD support:

```text
Dialogue
Music
SFX
Ambient
Master
```

Each audio clip may specify:

```text
volume
pan
fadeIn
fadeOut
sourceIn
sourceOut
speed
```

---

# 20. Dialogue Priority

When dialogue is required, mixing policies SHOULD allow dialogue ducking.

Conceptually:

```text
Dialogue active
   ↓
Music gain reduction
SFX gain reduction
   ↓
Dialogue remains intelligible
```

Exact gain values MUST be configuration-driven.

---

# 21. Audio Synchronization

Timeline synchronization MUST use the same canonical timebase as video.

The system MUST account for:

```text
source offsets
trim
speed
latency
sample rate conversion
```

Audio drift MUST be detected during final QC.

---

# 22. Loudness and Mastering

Render profiles MAY define:

```text
integrated loudness target
true peak limit
normalization mode
```

Mastering SHOULD occur through explicit filters or renderer stages.

The renderer MUST NOT silently apply an undocumented loudness transformation.

---

# 23. Subtitle Track

Subtitle clips SHOULD contain:

```text
text
startTime
endTime
style
language
speaker
```

Subtitle rendering may be:

```text
burned-in
sidecar
both
```

The render profile MUST specify the intended behavior.

---

# 24. Subtitle Safety

Subtitle text MUST be escaped safely for the selected renderer/filter.

The system MUST protect against:

- filter injection
- malformed markup
- invalid encoding
- path traversal through subtitle references

External subtitle files MUST be treated as untrusted input.

---

# 25. Captions and Accessibility

The system SHOULD support metadata for:

```text
language
forced
closed-caption
SDH
speaker labels
```

Accessibility output is policy/profile-driven.

---

# 26. Effects

Effects SHOULD be represented as structured data rather than arbitrary shell strings.

Example:

```text
Effect
 ├── type
 ├── parameters
 ├── startTime
 ├── duration
 └── version
```

Arbitrary command injection MUST NOT be possible through effect parameters.

---

# 27. Color Processing

The renderer MAY support:

```text
brightness
contrast
saturation
gamma
LUT
color-space conversion
```

Color transformations MUST be explicit and versioned.

Source and target color spaces SHOULD be known where possible.

---

# 28. Renderer Abstraction

The domain MUST define a renderer interface independent of FFmpeg.

Conceptually:

```text
validate(timeline, profile)
plan(timeline, profile) -> RenderPlan
render(renderPlan, options) -> RenderResult
cancel(renderJob)
healthCheck()
```

An FFmpeg implementation is the default candidate but not the only possible renderer.

---

# 29. FFmpeg Boundary

FFmpeg-specific flags, filter graphs, codec names, and command-line construction MUST live inside the renderer adapter.

Domain code MUST NOT construct raw FFmpeg command strings.

The adapter SHOULD build arguments using structured arrays rather than shell concatenation.

---

# 30. Render Plan

Before expensive rendering, the system SHOULD create a deterministic Render Plan containing:

```text
source asset versions
asset hashes
tracks
clips
transitions
effects
audio mix
subtitle behavior
render profile
encoder configuration
software/runtime versions
```

The Render Plan provides a reproducible execution snapshot.

---

# 31. Render Profile

A Render Profile SHOULD contain:

```text
profileId
version
container
videoCodec
audioCodec
width
height
frameRate
pixelFormat
bitrate/crf
preset
audioSampleRate
channels
loudnessPolicy
subtitlePolicy
colorPolicy
```

Examples:

```text
SHORT_VERTICAL_1080P
SHORT_HORIZONTAL_1080P
SQUARE_1080P
MASTER_4K
```

Profiles MUST be versioned.

---

# 32. Codec Policy

The renderer MUST use explicit codec configuration.

Common output example:

```text
Container: MP4
Video: H.264
Audio: AAC
```

Other codecs MAY be supported when the target platform requires them.

The renderer MUST validate that the selected combination is compatible.

---

# 33. Hardware Encoding

Hardware acceleration MAY be used when available.

Examples:

```text
NVENC
VAAPI
VideoToolbox
AMF
QSV
```

Hardware encoding is an optimization, not a required dependency for the core architecture.

The system MUST provide a compatible software fallback where policy permits.

---

# 34. Resource Requirements

Render jobs MUST declare resource requirements where practical:

```text
CPU
RAM
GPU
VRAM
storage
expected duration
```

The Queue Scheduler/Resource Manager controls execution.

Rendering MUST NOT bypass the central scheduler for resource allocation.

---

# 35. Render Staging

Render outputs MUST be written to staging first.

Sequence:

```text
Render Plan
 ↓
validate source assets
 ↓
reserve resources
 ↓
render to staging
 ↓
verify output
 ↓
hash
 ↓
probe
 ↓
final QC
 ↓
promote immutable asset
```

Never expose a partially rendered output as the final asset.

---

# 36. Render Job Lifecycle

Recommended:

```text
PENDING
QUEUED
RUNNING
PAUSED
RETRYING
COMPLETED
FAILED
CANCELLED
```

Completion requires:

```text
render process success
AND
output exists
AND
output readable
AND
hash valid
AND
technical validation passes
AND
required final QC passes
```

---

# 37. Progress Reporting

Render progress SHOULD be normalized to:

```text
0.0 → 1.0
```

Progress events should include:

```text
jobId
phase
progress
framesProcessed
framesTotal when known
elapsed
eta when reliable
```

ETA must not be presented as exact when it is only an estimate.

---

# 38. Cancellation

Render cancellation MUST be cooperative where possible.

Sequence:

```text
cancel requested
 ↓
renderer receives signal
 ↓
process stops
 ↓
staging cleanup
 ↓
job → CANCELLED
```

A cancelled render MUST NOT leave a falsely completed final asset.

---

# 39. Retry Policy

Retry only failures that are plausibly transient.

Retryable examples:

```text
storage timeout
worker interruption
temporary provider/resource failure
```

Non-retryable examples:

```text
invalid timeline
missing source asset
unsupported codec
invalid filter parameters
corrupt input
```

Retry policy must be bounded and scheduler-controlled.

---

# 40. Determinism

The render of identical:

```text
timeline version
asset versions
asset hashes
render profile
renderer version
software version
```

SHOULD produce equivalent output within declared encoder nondeterminism.

Render provenance MUST record the actual versions used.

---

# 41. Reproducibility

A completed render SHOULD retain:

```text
timelineId
timelineVersion
renderProfileId
renderProfileVersion
sourceAssetIds
sourceAssetHashes
renderer
rendererVersion
FFmpeg version
encoder configuration
createdAt
```

This enables later diagnosis and reproduction.

---

# 42. Render Provenance

The final Render Asset MUST link to:

```text
RenderJob
RenderPlan
Timeline version
Source Asset versions
Renderer version
Render Profile version
```

It MUST integrate with `ASSET_STORAGE_PROVENANCE_SPECIFICATION.md`.

---

# 43. Render Caching

Render caching MAY reuse previous outputs when the complete render fingerprint matches.

Fingerprint SHOULD include:

```text
timeline hash
source asset hashes
render profile hash
renderer version
filter/effect versions
subtitle inputs
encoder configuration
```

A cache hit MUST be integrity-verified.

Changing any render-affecting input invalidates the cache.

---

# 44. Incremental Rendering

Future implementations MAY render only changed timeline regions.

Incremental rendering MUST preserve deterministic composition boundaries.

Do not optimize incrementally until full-render correctness is established.

---

# 45. Timeline Validation

Before rendering, validate:

```text
all asset references resolve
asset versions exist
source ranges are valid
clip durations are valid
track overlaps are legal
transitions are legal
effects are valid
subtitle ranges are valid
audio configuration is valid
render profile is compatible
required assets are QC-approved
```

Validation failures MUST prevent expensive rendering.

---

# 46. Required QC Gate

A timeline SHOULD reference only assets that satisfy the required QC policy.

For example:

```text
Best Take
  ↓
QC PASSED
  ↓
Timeline Clip
```

A timeline MAY contain review/pending assets only in explicitly non-production draft mode.

Production render MUST reject unresolved blockers.

---

# 47. Timeline Locking

When a production render begins:

```text
Timeline version → immutable snapshot
```

Edits create a new timeline version.

This prevents a running render from changing underneath the renderer.

---

# 48. Render Snapshot

Every production RenderJob SHOULD capture a snapshot or immutable references to:

```text
Timeline
Assets
QC decisions
Render Profile
Renderer configuration
```

A later edit must not alter the historical render.

---

# 49. Preview Rendering

Preview rendering SHOULD be separate from production rendering.

Preview profiles may use:

```text
lower resolution
faster codec
lower bitrate
reduced effects
proxy media
```

Preview output MUST be marked as preview and MUST NOT accidentally become the final published asset.

---

# 50. Proxy Media

Large projects MAY use proxy assets.

Proxy mapping MUST be explicit:

```text
sourceAssetVersion
proxyAssetVersion
```

Final rendering MUST use the authoritative source unless a profile explicitly permits proxy output.

---

# 51. Missing Media

If a required asset is unavailable:

```text
render → BLOCKED
```

The system MUST report the exact missing Asset IDs.

It MUST NOT silently substitute unrelated media.

---

# 52. Audio/Video Duration Rules

The renderer MUST define deterministic handling for mismatched durations.

Possible policies:

```text
TRIM
PAD
LOOP
HOLD
FAIL
```

Default production behavior should prefer explicit failure over silent semantic alteration.

---

# 53. Frame Rate Conversion

When source and timeline frame rates differ, conversion policy MUST be explicit.

Possible methods:

```text
DUPLICATE
DROP
BLEND
MOTION_INTERPOLATION
```

Interpolation is an optional AI/media processing stage and must remain distinct from basic renderer behavior.

---

# 54. Resolution Conversion

Scaling MUST use an explicit algorithm/profile.

Where high-quality upscaling is required:

```text
source
 ↓
upscale job
 ↓
QC
 ↓
asset version
 ↓
timeline/render
```

Do not hide an expensive AI upscale inside ordinary rendering.

---

# 55. Subtitles in Final Output

For burned-in subtitles:

```text
subtitle asset/data
 ↓
validated timing/text
 ↓
renderer filter
```

For sidecar subtitles:

```text
final video
+
subtitle artifact
```

Both artifacts should share common provenance.

---

# 56. Export Formats

The architecture SHOULD permit:

```text
MP4
MOV
MKV
WebM
image sequences
WAV
AAC
other profile-defined formats
```

Supported formats are configuration-driven.

The MVP may start with MP4/H.264/AAC while retaining an extensible profile model.

---

# 57. Platform Profiles

Publishing targets may define profiles for:

```text
short-form vertical
standard horizontal
square
archive/master
mobile preview
```

The render subsystem should produce platform-compliant artifacts without embedding platform-specific assumptions in core domain models.

---

# 58. Final Output Validation

After rendering, final validation MUST include:

```text
file exists
file size valid
hash calculated
container parse succeeds
video stream valid
audio stream valid when required
resolution correct
frame rate correct
duration within tolerance
codec/profile compatible
subtitle output valid when required
```

Then run final QC according to `MEDIA_QC_CONTINUITY_SPECIFICATION.md`.

---

# 59. Output Promotion

Only after validation/QC:

```text
staging output
   ↓
final immutable blob
   ↓
Render Asset
   ↓
AVAILABLE
```

Database state and storage state must have recovery procedures for partial failures.

---

# 60. Publishing Boundary

Publishing MUST consume a validated final Asset.

Flow:

```text
Timeline
 ↓
Render
 ↓
Final QC
 ↓
Final Asset
 ↓
Publishing Job
```

Publishing MUST NOT render directly from arbitrary draft filesystem paths.

---

# 61. Security

Renderer inputs may be user-controlled and MUST be treated as untrusted.

Security requirements:

- no shell command concatenation from user input
- no arbitrary executable paths
- sanitize subtitle/filter parameters
- isolate renderer processes where practical
- enforce resource limits
- restrict filesystem access
- never expose storage credentials
- log command metadata safely without secrets

---

# 62. Process Isolation

FFmpeg or other renderer processes SHOULD run in a controlled environment.

Possible controls:

```text
container
sandbox
restricted user
CPU limit
RAM limit
disk quota
network restriction
filesystem allowlist
```

The renderer should not require unrestricted network access for local assets.

---

# 63. Temporary Files

All renderer temporary files MUST be job-scoped.

Example:

```text
/tmp/ai-content-factory/render/<renderJobId>/
```

Cleanup MUST happen on:

```text
success
failure
cancellation
worker crash recovery
TTL expiration
```

---

# 64. Storage Integration

Renderer source/output access MUST use the storage abstraction.

```text
Asset ID
 ↓
Storage Service
 ↓
materialize/stream
 ↓
Renderer
```

The renderer may use local temporary paths internally, but those paths are implementation details.

---

# 65. Database Integration

Recommended persistent entities:

```text
timelines
timeline_versions
tracks
clips
transitions
effects
render_profiles
render_jobs
render_plans
render_artifacts
```

Foreign keys and delete policies must protect active render dependencies.

---

# 66. API Integration

Recommended endpoints:

```text
GET    /api/v1/timelines/{timelineId}
POST   /api/v1/timelines
POST   /api/v1/timelines/{timelineId}/versions
POST   /api/v1/timelines/{timelineId}/validate
POST   /api/v1/timelines/{timelineId}/render
GET    /api/v1/render-jobs/{jobId}
POST   /api/v1/render-jobs/{jobId}/cancel
GET    /api/v1/render-jobs/{jobId}/events
GET    /api/v1/render-profiles
```

Long-running renders MUST follow the asynchronous Job contract.

---

# 67. Eventing

The renderer SHOULD emit:

```text
RENDER_QUEUED
RENDER_STARTED
RENDER_PROGRESS
RENDER_PAUSED
RENDER_RESUMED
RENDER_COMPLETED
RENDER_FAILED
RENDER_CANCELLED
RENDER_QC_STARTED
RENDER_QC_COMPLETED
RENDER_ARTIFACT_PUBLISHED
```

Events MUST be versioned and tolerant of duplicate/out-of-order delivery.

---

# 68. Observability

Metrics SHOULD include:

```text
render_jobs_total
render_success_rate
render_failure_rate
render_duration
render_fps
frames_processed
render_queue_wait
storage_read_bytes
storage_write_bytes
encoder_failures
qc_failures
cache_hit_rate
```

Record by render profile, renderer version, and hardware class where useful.

---

# 69. Cost and Performance

The renderer SHOULD optimize by:

- avoiding unnecessary asset copies
- using streaming where possible
- proxy previews
- render caching
- parallel independent preparation
- hardware acceleration where safe
- avoiding repeated decode/encode operations

Correctness takes priority over optimization.

---

# 70. Testing

## Unit Tests

Test:

- timeline validation
- time calculations
- clip mapping
- transitions
- transform calculations
- audio mixing rules
- subtitle timing
- render profile validation
- render fingerprinting

## Integration Tests

Test:

- FFmpeg adapter
- local storage
- media probing
- render staging
- cancellation
- retries
- final promotion

## Contract Tests

Verify:

```text
Timeline ↔ API
Timeline ↔ DB
Timeline ↔ Renderer
Asset ↔ Renderer
QC ↔ Renderer
RenderJob ↔ Queue
```

## Golden Render Tests

Use deterministic small media fixtures and verify:

- successful render
- expected duration
- expected resolution
- valid streams
- audio presence
- subtitles where required
- hash/provenance registration

---

# 71. Failure Injection

Test at least:

1. missing source asset
2. corrupted source
3. invalid clip range
4. unsupported codec
5. invalid subtitle
6. FFmpeg failure
7. process timeout
8. disk full
9. storage unavailable
10. worker crash
11. cancellation
12. QC rejection
13. render cache mismatch
14. stale timeline version
15. concurrent edit/render
16. output corruption
17. invalid encoder configuration

No failure may produce a false `COMPLETED` render.

---

# 72. Mock Renderer

CI SHOULD provide a deterministic mock renderer.

Mock output MUST still flow through:

```text
Timeline validation
→ RenderJob
→ RenderResult
→ Asset registration
→ Provenance
→ Final QC
```

Mock mode must not bypass production contracts.

---

# 73. Golden End-to-End

Canonical pipeline:

```text
Project
 ↓
Episode
 ↓
Story
 ↓
Scenes
 ↓
Shots
 ↓
Best Takes
 ↓
Timeline
 ↓
Timeline Validation
 ↓
Render Plan
 ↓
Mock/Real Renderer
 ↓
Staging Output
 ↓
Hash + Probe
 ↓
Final QC
 ↓
Final Render Asset
 ↓
Publishing
```

This is the minimum end-to-end acceptance path for the rendering architecture.

---

# 74. Non-Negotiable Rules

1. Timeline is a durable domain object, not UI state.
2. Timeline versions must be stable for production renders.
3. Clips reference logical immutable Asset versions, never arbitrary paths.
4. Time persistence must avoid floating-point drift.
5. Render profiles must be explicit and versioned.
6. FFmpeg details must remain behind a renderer abstraction.
7. User input must never become an unsafe shell command.
8. Rendering must use staging before final promotion.
9. Process success alone does not equal render success.
10. Final output must pass integrity, technical, and required final QC.
11. Missing assets must block production rendering.
12. Render jobs must use the central scheduler/resource manager.
13. Cancellation must not create a completed artifact.
14. Retry must be limited to retryable failures.
15. Render provenance must identify source assets, timeline, profile, and renderer versions.
16. Preview artifacts must never be confused with production finals.
17. Hardware acceleration is optional, not an architectural dependency.
18. Mock rendering must preserve the same logical contracts.
19. Historical renders must remain reproducible/auditable.
20. Publishing may consume only validated final Assets.

---

# 75. Implementation Order

### Phase 1 — Timeline Foundation

- timeline models
- versions
- tracks
- clips
- timebase
- validation

### Phase 2 — Audio/Subtitle

- dialogue
- music
- SFX
- mixing
- subtitles
- timing validation

### Phase 3 — Composition

- transforms
- z-order
- transitions
- effects
- color operations

### Phase 4 — Renderer

- renderer interface
- FFmpeg adapter
- render profiles
- render plans
- staging

### Phase 5 — Production Reliability

- scheduler integration
- resource management
- cancellation
- retries
- progress/events
- provenance

### Phase 6 — Final Quality

- final media validation
- final QC
- output promotion
- render caching
- deterministic golden tests

### Phase 7 — Advanced Optimization

- hardware encoding
- proxies
- incremental rendering
- parallel preparation
- performance tuning

---

# 76. Definition of Done

The Timeline/Rendering subsystem is complete only when:

- timeline persistence exists
- timeline versioning exists
- tracks/clips are modeled
- canonical time representation exists
- source mapping is validated
- transitions are validated
- audio/subtitle support exists
- render profiles are versioned
- renderer abstraction exists
- FFmpeg implementation is isolated
- render plans are reproducible
- staging output exists
- final promotion is atomic/recoverable
- cancellation works
- retry classification works
- scheduler/resource integration works
- render provenance is persisted
- final QC is enforced
- preview and production outputs are distinct
- storage abstraction is respected
- project isolation is enforced
- security controls exist
- mock renderer works offline
- contract tests pass
- golden render tests pass
- existing tests/build remain green
- no false-success render paths remain
- documentation matches implementation

---

# 77. Final Architecture Contract

```text
              Best Take Assets
                     │
                     ▼
              Timeline Version
                     │
                     ▼
             Timeline Validation
                     │
              ┌──────┴──────┐
              ▼             ▼
           Invalid         Ready
              │             │
           BLOCKED          ▼
                       Render Plan
                            │
                            ▼
                    Queue / Scheduler
                            │
                            ▼
                      Renderer Worker
                            │
                     ┌──────┴──────┐
                     ▼             ▼
                  Staging       Failure
                     │
                     ▼
                Hash + Probe
                     │
                     ▼
                  Final QC
                     │
              ┌──────┴──────┐
              ▼             ▼
           Rejected       Passed
                             │
                             ▼
                    Immutable Render Asset
                             │
                             ▼
                         Publishing
```

The rendering subsystem is therefore the deterministic bridge between creative decisions and a validated deliverable. It must preserve asset identity, timing, provenance, reproducibility, security, and quality from timeline edit through final published media.

**End of Specification — Version 1.0**
