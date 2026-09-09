# MEDIA QC & CONTINUITY SPECIFICATION

**Project:** AI Content Factory  
**Document Type:** Normative Engineering Specification  
**Version:** 1.0  
**Status:** Baseline / Implementation Reference

---

## 1. Purpose

This document defines the authoritative quality-control, media-validation, continuity, semantic validation, scoring, blocking, Best Take selection, and production-quality gates for AI Content Factory.

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

This specification is normative. QC is a production gate, not an optional UI decoration.

---

# 2. Quality Philosophy

AI generation is probabilistic. A successful provider response does not imply a usable production result.

The factory MUST distinguish:

```text
Generation success
≠
Asset validity
≠
Media quality
≠
Continuity quality
≠
Semantic quality
≠
Final acceptance
```

A job may complete technically while its output is rejected by QC.

The pipeline therefore follows:

```text
Generate
  ↓
Validate
  ↓
Probe
  ↓
QC
  ↓
Score
  ↓
Accept / Reject / Review
  ↓
Best Take
  ↓
Timeline / Render
```

---

# 3. QC Layers

The canonical QC stack is:

```text
1. Integrity QC
2. Technical QC
3. Media QC
4. Continuity QC
5. Semantic QC
6. Policy / License QC
7. Composite Decision
```

Each layer has a distinct responsibility.

---

# 4. QC Result Contract

A QC result SHOULD contain:

```text
id
projectId
assetId
jobId
qcType
status
score
threshold
severity
issues[]
metrics
rulesetVersion
modelVersion
createdAt
completedAt
```

Optional:

```text
parentQcId
comparisonAssetIds[]
referenceAssetIds[]
reviewRequired
reviewerId
explanation
```

Statuses SHOULD include:

```text
PENDING
RUNNING
PASSED
PASSED_WITH_WARNINGS
FAILED
BLOCKED
REVIEW_REQUIRED
SKIPPED
```

---

# 5. Severity

Canonical issue severities:

```text
INFO
WARNING
ERROR
BLOCKER
```

Meaning:

- `INFO`: informational; no acceptance impact.
- `WARNING`: quality concern; normally non-blocking.
- `ERROR`: meaningful defect; may block depending on policy.
- `BLOCKER`: output cannot enter the affected production stage.

Rules MUST be explicit about which severities block which pipeline stages.

---

# 6. Integrity QC

Integrity QC verifies that the Asset exists and is internally consistent.

Checks SHOULD include:

- blob exists
- expected bytes are readable
- content hash matches
- size is non-zero where required
- asset/blob relationship is valid
- storage reference resolves
- file is not truncated
- decompression/decoder initialization succeeds

Failure example:

```text
hash mismatch → BLOCKER
missing blob → BLOCKER
zero-byte required video → BLOCKER
```

An integrity failure MUST prevent normal downstream consumption.

---

# 7. Technical QC

Technical QC verifies whether the media is technically usable.

## Video

Check at least:

```text
container
codec
resolution
width/height
frame rate
frame count/duration
bit rate
pixel format
video stream count
```

## Audio

Check:

```text
container
codec
sample rate
channels
bit depth when available
duration
bit rate
stream count
```

## Images

Check:

```text
format
width
height
color mode
alpha support when relevant
file readability
```

Technical rules are configuration-driven and MUST NOT be hard-coded to one output format globally.

---

# 8. Technical Validation Examples

Possible blockers:

```text
unsupported codec
missing required stream
invalid container
corrupt decoder structure
resolution below contract minimum
zero duration
unreadable frame
unexpected frame rate when strict contract applies
```

A technically valid file can still fail later QC.

---

# 9. Media QC

Media QC evaluates perceptual and production-level defects.

Depending on asset type, checks may include:

### Video

- severe flicker
- black frames
- frozen frames
- corrupted frames
- abrupt visual discontinuities
- severe motion artifacts
- malformed interpolation
- temporal instability
- obvious generation artifacts
- severe camera/object deformation

### Image

- malformed anatomy where relevant
- duplicate/merged objects
- broken geometry
- severe artifacting
- unintended text
- framing problems
- visual noise

### Audio

- clipping
- silence
- excessive noise
- distortion
- unexpected duration
- discontinuities
- synchronization defects

The exact detectors are modular and model/provider agnostic.

---

# 10. Audio-Visual Synchronization

For audiovisual assets, QC SHOULD validate:

```text
video duration
vs
voice/dialogue duration
vs
music/SFX placement
```

Potential issues:

```text
lip-sync offset
voice starts too early
voice ends too late
missing dialogue
audio drift
```

Tolerance MUST be configurable per workflow.

---

# 11. Continuity QC

Continuity ensures that adjacent shots/scenes remain visually and logically coherent.

Continuity dimensions include:

```text
Character identity
Character appearance
Wardrobe
Hair/accessories
Age/physical traits
Location
World properties
Lighting
Time of day
Weather
Props
Object positions
Camera geography
Screen direction
Action state
Dialogue context
Narrative state
```

Continuity is not limited to image similarity.

---

# 12. Character Continuity

Each Character SHOULD have a Character Bible containing stable attributes.

Continuity comparison may evaluate:

```text
face embedding
visual embedding
body proportions
hair
clothing
colors
accessories
age cues
signature props
```

Reference images/assets SHOULD be immutable inputs to continuity checks.

A generated shot that visually resembles a different character should fail or require review according to policy.

---

# 13. World and Location Continuity

World/location continuity SHOULD evaluate:

- geometry/layout
- architectural identity
- major objects
- color palette
- environmental features
- time of day
- weather
- lighting direction
- recurring landmarks

Small stochastic variation may be allowed.

Major structural contradictions SHOULD produce `ERROR` or `BLOCKER` according to project policy.

---

# 14. Prop and Object Continuity

Important recurring objects SHOULD be represented as continuity anchors.

Examples:

```text
phone
car
weapon when legally/policy permitted
bag
chair
microphone
signature object
```

The QC system should track attributes relevant to narrative consistency:

```text
presence
position
orientation
color
shape
state
```

---

# 15. Temporal Continuity

QC SHOULD compare state transitions across shots.

Example:

```text
Shot A: character holding cup
Shot B: cup suddenly absent
```

Possible outcomes:

```text
INFO/WARNING if transition is narratively explained
ERROR if inconsistent
BLOCKER if it breaks the scene's required action
```

Continuity must understand narrative context when possible.

---

# 16. Screen Direction and Spatial Continuity

For sequences requiring coherent geography, QC SHOULD evaluate:

- camera orientation
- left/right screen position
- subject entry/exit direction
- relative object positions
- shot-reverse-shot consistency
- major axis violations

Not every cinematic axis break is an error; rules MUST permit intentional exceptions.

---

# 17. Semantic QC

Semantic QC asks whether the generated media actually matches the intended content.

Inputs may include:

```text
story
scene description
shot prompt
dialogue
character bible
world bible
reference assets
constraints
```

Possible checks:

```text
correct characters present
correct action
correct location
correct object
correct emotional state
correct shot type
correct dialogue meaning
correct scene intent
```

---

# 18. Vision-Language Evaluation

Semantic QC MAY use:

- vision-language models
- image/video embeddings
- object detection
- OCR
- speech-to-text
- face/identity comparison
- action recognition
- custom classifiers

Model choice MUST be registry-driven.

No semantic model may be assumed permanently available.

---

# 19. OCR QC

If a scene or asset is expected to contain text, OCR MAY validate:

- presence
- expected words
- spelling
- placement
- legibility

If text is not expected, unexpected generated text may be flagged.

OCR checks MUST be policy-driven because many generative models produce accidental text.

---

# 20. Dialogue and Speech QC

Dialogue assets SHOULD be checked for:

```text
transcription correctness
duration
speaker identity
pronunciation where detectable
silence/clipping
language
volume consistency
```

For generated dialogue:

```text
TTS
 ↓
ASR transcription
 ↓
semantic comparison to source dialogue
```

Large deviations SHOULD fail or require regeneration.

---

# 21. Lip-Sync QC

Lip-sync QC SHOULD evaluate alignment between:

```text
spoken phonetic timing
mouth motion
audio waveform
```

The result SHOULD include a normalized score and confidence.

A failed lip-sync score may trigger:

```text
retry same model
retry alternate model
regenerate TTS
regenerate video
review
```

Fallback policy is defined by job/workflow configuration.

---

# 22. Music and SFX QC

Music/SFX checks may include:

- correct duration
- no unexpected silence
- no clipping
- acceptable loudness
- correct placement
- semantic suitability
- no forbidden content according to project policy

Music must not obscure required dialogue unless intentionally mixed that way.

---

# 23. Loudness and Audio Mix

The audio pipeline SHOULD support configurable loudness targets.

Checks may include:

```text
integrated loudness
true peak
short-term loudness
dialogue/music balance
```

Exact targets MUST be configuration-driven for the target platform.

QC SHOULD distinguish a warning from a hard failure where the deviation is recoverable during mastering/rendering.

---

# 24. Subtitle QC

Subtitle validation SHOULD include:

- syntax
- timing
- overlap
- reading duration
- text completeness
- synchronization
- line length
- forbidden/invalid characters

Subtitles MUST NOT overlap in invalid ways unless the format explicitly permits it.

---

# 25. Policy and License QC

QC MAY block assets based on:

```text
licenseStatus
content policy
project restrictions
provider restrictions
commercial-use requirements
attribution requirements
```

Canonical license statuses:

```text
VERIFIED
UNKNOWN
RESTRICTED
BLOCKED
```

An asset with `BLOCKED` licensing status MUST NOT enter a production path requiring permitted rights.

`UNKNOWN` is not equivalent to `VERIFIED`.

---

# 26. Rule Engine

QC rules MUST be configurable.

Conceptually:

```text
Rule
 ├── id
 ├── version
 ├── qcType
 ├── metric
 ├── operator
 ├── threshold
 ├── severity
 ├── action
 └── enabled
```

Example:

```text
rule: VIDEO_MIN_WIDTH
metric: width
operator: >=
threshold: 1080
severity: ERROR
```

Rules SHOULD be versioned so historical QC decisions remain reproducible.

---

# 27. Composite Scoring

Each QC layer MAY produce a normalized score:

```text
0.0 → 1.0
```

A composite score can be calculated using weighted components:

```text
score =
  w_integrity * integrityScore +
  w_technical * technicalScore +
  w_media * mediaScore +
  w_continuity * continuityScore +
  w_semantic * semanticScore
```

Weights MUST be workflow-configurable.

A high composite score MUST NOT override a hard blocker.

---

# 28. Confidence

Automated QC SHOULD report confidence separately from quality score.

Example:

```text
qualityScore = 0.91
confidence = 0.63
```

Low confidence SHOULD trigger review or conservative decision policies.

Quality and confidence are not interchangeable.

---

# 29. Acceptance Policy

A workflow MAY define:

```text
minimumScore
minimumConfidence
allowedWarnings
blockedSeverities
requiredQcTypes
```

Acceptance example:

```text
PASS when:
- all required QC types completed
- no BLOCKER
- no disallowed ERROR
- score >= threshold
- confidence >= threshold
```

---

# 30. Hard Blockers

Typical blockers include:

```text
missing/corrupt asset
hash mismatch
unreadable media
missing required stream
invalid required format
critical continuity contradiction
critical semantic mismatch
policy/license block
unsafe/forbidden output according to configured policy
render output invalid
```

The exact blocker set is policy-driven.

---

# 31. Review Queue

Automated QC MUST support a human-review path.

Possible states:

```text
REVIEW_REQUIRED
APPROVED
REJECTED
OVERRIDDEN
```

An override MUST record:

```text
reviewer
reason
timestamp
previousDecision
newDecision
```

A human override MUST NOT erase the automated QC evidence.

---

# 32. Best Take Selection

Best Take selection SHOULD be deterministic for the same inputs and scoring policy.

Candidate inputs:

```text
technical score
media score
continuity score
semantic score
lip-sync score
audio score
render readiness
cost
latency
human approval
```

Example conceptual score:

```text
bestTakeScore =
  qualityWeight * quality +
  continuityWeight * continuity +
  semanticWeight * semantic +
  syncWeight * sync -
  artifactPenalty -
  failurePenalty
```

No candidate with a hard blocker may be selected.

---

# 33. Best Take Tie-Breaking

Tie-breaking SHOULD be stable.

Recommended order:

1. no blockers
2. higher composite quality
3. higher semantic/continuity score
4. human approval
5. higher confidence
6. lower artifact count
7. lower cost/latency where configured
8. deterministic stable ID ordering

Random tie-breaking MUST NOT be used in production.

---

# 34. Regeneration Decisions

QC should produce actionable failure classifications.

Example:

```text
BAD_CONTINUITY
BAD_PROMPT_ALIGNMENT
BAD_ANATOMY
BAD_CAMERA
BAD_LIP_SYNC
BAD_AUDIO
BAD_DURATION
BAD_TECHNICAL_FORMAT
PROVIDER_ARTIFACT
MODEL_UNAVAILABLE
LICENSE_BLOCKED
```

The orchestrator may use these classifications to select a different remediation path.

---

# 35. Retry vs Regenerate

A technical infrastructure failure is not the same as a bad generation.

Examples:

```text
GPU timeout → retryable infrastructure error
provider 503 → retryable
invalid generated anatomy → regeneration
semantic mismatch → regeneration
hash mismatch → storage/integrity recovery
```

Retry policy MUST NOT endlessly retry outputs that are deterministically failing QC.

---

# 36. Multi-Model QC

Critical workflows MAY use more than one evaluator.

Example:

```text
Detector A
   +
Detector B
   +
VLM
   ↓
Composite decision
```

Evaluator disagreement SHOULD lower confidence or trigger review.

The system MUST retain which evaluators contributed to a decision.

---

# 37. Reference Assets

QC SHOULD compare outputs against authoritative references when available.

Examples:

```text
Character reference
Location reference
Storyboard
Previous shot
Dialogue transcript
Style bible
```

Reference assets MUST be identified by stable Asset IDs and immutable versions.

---

# 38. Continuity Memory

Series/episode continuity SHOULD maintain a structured memory containing:

```text
character state
wardrobe state
prop state
location state
time state
weather
relationships
story state
previous shot context
```

QC can compare a candidate against this memory instead of relying only on the immediate previous frame.

---

# 39. Scene-Level QC

Scene QC SHOULD aggregate shot-level evidence.

Potential checks:

- all required shots exist
- required characters appear
- continuity holds across shots
- dialogue coverage exists
- duration is within target
- no unresolved blockers
- scene narrative objective is represented

---

# 40. Episode-Level QC

Episode QC SHOULD evaluate:

```text
story completeness
scene completeness
shot completeness
continuity
audio consistency
subtitle consistency
runtime
render integrity
policy/license state
```

Episode acceptance MUST not be based solely on the final file's existence.

---

# 41. Final Render QC

The final render MUST undergo a dedicated final QC pass.

At minimum:

```text
file exists
hash valid
container valid
codec valid
resolution correct
duration correct
audio present where required
video decodable
no catastrophic corruption
subtitles valid where required
```

Platform-specific checks may be added.

---

# 42. QC Idempotency

QC jobs SHOULD be idempotent.

Repeated evaluation with the same:

```text
asset version
ruleset version
model/evaluator version
configuration
```

should produce equivalent results within declared nondeterminism limits.

Existing valid QC records may be reused when the evaluation identity matches.

---

# 43. QC Caching

QC results MAY be cached by a fingerprint containing:

```text
assetHash
assetVersion
qcType
rulesetVersion
evaluatorModelVersion
configurationHash
```

Changing any relevant input MUST invalidate the cache.

---

# 44. Observability

Metrics SHOULD include:

```text
qc_jobs_total
qc_pass_rate
qc_failure_rate
qc_blocker_rate
review_rate
regeneration_rate
best_take_success_rate
average_qc_duration
qc_model_latency
continuity_failure_rate
semantic_failure_rate
technical_failure_rate
```

Track metrics by provider/model/version where useful.

---

# 45. Explainability

QC results SHOULD explain the decision in structured form.

Example:

```text
status: FAILED
reasonCode: BAD_CONTINUITY
metric: character_identity_similarity
value: 0.41
threshold: 0.78
severity: ERROR
```

Human-readable explanations may accompany machine-readable reasons.

---

# 46. Security

QC inputs may contain private project media.

Therefore:

- project isolation MUST apply
- evaluator access MUST be scoped
- secrets MUST NOT be embedded in prompts/logs
- sensitive media MUST not be sent to external evaluators unless policy permits it
- external provider use MUST be explicit and auditable

---

# 47. External Evaluators

External vision/audio/LLM evaluators MUST be treated as providers.

They require:

```text
provider registry
model registry
capability declaration
license/policy declaration
health status
timeout
retry policy
provenance
```

The QC engine must remain provider-agnostic.

---

# 48. Local QC

Local-first mode SHOULD support local evaluators when available.

Examples:

```text
local FFprobe
local image analysis
local embeddings
local ASR
local VLM
```

The absence of a local evaluator should produce an explicit `UNAVAILABLE`/`SKIPPED` condition, not a fabricated PASS.

---

# 49. Mock QC

CI MUST support deterministic mock QC.

Mock QC SHOULD allow tests to inject:

```text
PASS
WARNING
FAIL
BLOCKER
REVIEW_REQUIRED
```

This permits testing orchestrator behavior without requiring GPU inference.

---

# 50. Failure Recovery

If QC infrastructure fails:

```text
QC provider unavailable
```

is not equivalent to:

```text
asset passed QC
```

The job SHOULD enter a state such as:

```text
RETRYING
PAUSED
REVIEW_REQUIRED
```

according to policy.

---

# 51. Event Integration

QC SHOULD emit events such as:

```text
QC_STARTED
QC_PROGRESS
QC_COMPLETED
QC_FAILED
QC_BLOCKED
QC_REVIEW_REQUIRED
BEST_TAKE_SELECTED
REGENERATION_REQUESTED
```

Events MUST include stable IDs and schema versions and tolerate duplication/out-of-order delivery.

---

# 52. API Integration

Recommended endpoints:

```text
POST /api/v1/assets/{assetId}/qc
GET  /api/v1/assets/{assetId}/qc
GET  /api/v1/qc/{qcId}
POST /api/v1/qc/{qcId}/review
POST /api/v1/shots/{shotId}/best-take
GET  /api/v1/shots/{shotId}/takes
```

Exact endpoint behavior must remain consistent with `API_SPECIFICATION.md`.

---

# 53. Database Integration

QC persistence SHOULD support:

```text
qc_results
qc_issues
qc_metrics
qc_evaluations
qc_references
best_takes
review_decisions
```

Historical QC results MUST remain traceable to the asset version and ruleset/evaluator versions used.

---

# 54. Versioning

Every production QC decision SHOULD identify:

```text
rulesetVersion
evaluatorVersion
assetVersion
schemaVersion
```

Changing a QC rule does not retroactively mutate historical results.

A new evaluation produces a new result.

---

# 55. Golden QC Flow

The canonical deterministic test is:

```text
Mock generated asset
 ↓
Integrity QC
 ↓
Technical QC
 ↓
Media QC
 ↓
Continuity QC
 ↓
Semantic QC
 ↓
Composite score
 ↓
Acceptance decision
 ↓
Best Take
 ↓
Timeline
 ↓
Render
 ↓
Final QC
```

The test suite MUST cover both successful and deliberately failing variants.

---

# 56. Critical Failure Tests

At minimum test:

1. corrupt blob
2. hash mismatch
3. unreadable video
4. missing audio
5. invalid resolution
6. black frames
7. frozen frames
8. severe artifact
9. wrong character
10. wrong location
11. wrong action
12. continuity break
13. dialogue mismatch
14. lip-sync failure
15. subtitle timing failure
16. license block
17. evaluator unavailable
18. low confidence
19. conflicting evaluators
20. no valid Best Take
21. human override
22. stale QC cache
23. duplicate QC event
24. out-of-order QC event

---

# 57. No Valid Take

If all generated takes fail required QC:

```text
Shot → BLOCKED / REGENERATION_REQUIRED
```

The system MUST NOT silently select the least-bad invalid output as Best Take.

The orchestrator should then determine whether to:

- regenerate
- switch model
- switch provider
- change prompt/constraints
- request human review
- pause the workflow

---

# 58. Human-in-the-Loop Policy

Human review is an explicit production state.

Reviewers should see:

```text
candidate
reference assets
QC scores
issues
confidence
comparison takes
provenance
```

Approval selects a specific immutable asset version.

---

# 59. Cost-Aware QC

The pipeline MAY use tiered evaluation:

```text
cheap technical checks
   ↓
cheap artifact checks
   ↓
continuity
   ↓
semantic VLM
   ↓
human review if needed
```

Expensive evaluators SHOULD run only when cheaper gates do not already establish failure.

---

# 60. Performance

QC MUST avoid unnecessary full-media copies.

Prefer:

- streaming reads
- frame sampling
- cached probes
- hash reuse
- parallel independent checks
- bounded concurrency

Full-frame/full-video analysis should be reserved for policies that require it.

---

# 61. Resource Management

QC workloads consume CPU/GPU/RAM/storage and MUST enter the same resource-aware scheduling architecture as generation jobs.

Examples:

```text
VLM continuity check → GPU
FFprobe → CPU
thumbnail → CPU
ASR → GPU/CPU
embedding → GPU
```

The Model Registry and Queue Scheduler determine actual resource placement.

---

# 62. Non-Negotiable Rules

1. Provider success does not equal QC success.
2. Asset integrity MUST be checked before production consumption.
3. Hard blockers MUST prevent invalid downstream selection.
4. QC results MUST reference immutable asset versions.
5. QC rules and evaluator versions MUST be traceable.
6. Quality score MUST NOT override a hard blocker.
7. Confidence MUST be separate from quality score.
8. `UNKNOWN` licensing MUST NOT be treated as verified-safe.
9. Missing evaluator capability MUST NOT become an automatic PASS.
10. Failed candidates MUST NOT silently become Best Take.
11. Best Take selection MUST be deterministic under identical inputs/policy.
12. Human overrides MUST preserve automated evidence.
13. Continuity must use authoritative references when available.
14. Regeneration must be distinguished from infrastructure retry.
15. QC must remain provider/model agnostic.
16. Mock QC must follow production contracts.
17. Historical QC decisions MUST remain reproducible and auditable.
18. QC events MUST tolerate duplication and reordering.
19. Project isolation MUST apply to QC data and media.
20. Final render MUST receive a dedicated final QC gate.

---

# 63. Implementation Order

### Phase 1 — Integrity & Technical QC

- asset integrity checks
- hash verification
- media probing
- basic format validation
- deterministic QC contracts

### Phase 2 — Media QC

- frame sampling
- black/frozen frame detection
- artifact checks
- audio checks
- sync checks

### Phase 3 — Continuity

- Character Bible integration
- reference assets
- embeddings
- scene/location state
- temporal continuity

### Phase 4 — Semantic QC

- VLM interface
- OCR
- ASR comparison
- action/object validation

### Phase 5 — Scoring & Best Take

- normalized metrics
- weighted scoring
- blocker policies
- deterministic tie-breaking
- Best Take persistence

### Phase 6 — Review & Recovery

- review queue
- human overrides
- regeneration classification
- model/provider fallback

### Phase 7 — Production Optimization

- QC caching
- tiered QC
- parallel execution
- metrics
- evaluator benchmarking

---

# 64. Definition of Done

The QC/Continuity subsystem is complete only when:

- integrity QC exists
- technical QC exists
- media QC exists
- continuity QC exists
- semantic QC exists where required
- policy/license QC exists where required
- rule versions are persisted
- evaluator/model versions are persisted
- quality and confidence are separate
- blockers are enforced
- review flow exists
- Best Take selection is deterministic
- failed candidates cannot become Best Take
- regeneration reasons are machine-readable
- QC caching is fingerprinted safely
- project isolation is enforced
- mock QC works offline
- unit/integration/contract tests pass
- Golden E2E passes
- final render QC exists
- existing tests/build remain green
- no fake PASS paths remain
- documentation matches implementation

---

# 65. Final Architecture Contract

```text
                 Asset
                   │
                   ▼
            Integrity QC
                   │
                   ▼
           Technical QC
                   │
                   ▼
              Media QC
                   │
                   ▼
          Continuity QC
                   │
                   ▼
            Semantic QC
                   │
          ┌────────┴────────┐
          ▼                 ▼
       Blocked          Score/Review
                            │
                   ┌────────┴────────┐
                   ▼                 ▼
               Rejected          Accepted
                                     │
                                     ▼
                                Best Take
                                     │
                                     ▼
                                  Timeline
                                     │
                                     ▼
                                  Render
                                     │
                                     ▼
                                Final QC
                                     │
                              ┌──────┴──────┐
                              ▼             ▼
                           Publish       Block
```

QC is therefore a first-class subsystem connecting Assets, AI generation, continuity, timeline construction, rendering, and publishing. The factory must optimize for **usable output**, not merely successful generation.

**End of Specification — Version 1.0**
