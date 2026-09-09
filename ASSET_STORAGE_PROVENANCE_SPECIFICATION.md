# ASSET STORAGE & PROVENANCE SPECIFICATION

**Project:** AI Content Factory  
**Document Type:** Normative Engineering Specification  
**Version:** 1.0  
**Status:** Baseline / Implementation Reference  

---

## 1. Purpose

This document defines the authoritative architecture and implementation contract for files, media assets, blobs, storage, metadata, provenance, lineage, upload/download, integrity, retention, access control, and asset lifecycle across AI Content Factory.

It complements:

- `PROJECT_RULES.md`
- `DEVELOPER_IMPLEMENTATION_GUIDE.md`
- `CONTRACTS_SPECIFICATION.md`
- `DATABASE_SCHEMA_SPECIFICATION.md`
- `API_SPECIFICATION.md`
- `WORKER_PROVIDER_ARCHITECTURE.md`
- `AI_MODEL_REGISTRY_SPECIFICATION.md`
- `QUEUE_SCHEDULER_SPECIFICATION.md`

This document is normative. Implementations MUST follow these rules unless a later version explicitly supersedes them.

---

## 2. Core Principle

An **Asset is a logical application object**. A **Blob/File is the physical stored content**.

They MUST NOT be treated as the same abstraction.

Conceptually:

```text
Asset
  ├── identity
  ├── semantic type
  ├── lifecycle/status
  ├── metadata
  ├── provenance
  ├── project ownership
  ├── version/lineage
  └── Blob reference
          ├── storage provider
          ├── storage key
          ├── byte size
          ├── hash/checksum
          └── physical location
```

This separation allows storage migration, deduplication, derived assets, immutable provenance, signed downloads, local-first operation, and cloud/object-storage backends without changing domain contracts.

---

# 3. Asset Identity

Every Asset MUST have a globally unique opaque identifier.

Recommended:

- UUIDv4/v7
- ULID
- another collision-resistant opaque identifier

The API MUST expose asset IDs as opaque values. Clients MUST NOT infer filesystem paths from IDs.

Minimum logical fields:

```text
id
projectId
assetType
status
blobId
version
parentAssetId
createdAt
updatedAt
```

Optional fields include:

```text
name
description
mimeType
extension
sizeBytes
durationMs
width
height
frameRate
sampleRate
channels
codec
container
hash
metadata
thumbnailAssetId
previewAssetId
```

---

# 4. Asset Types

The canonical asset taxonomy SHOULD include:

```text
STORY
CHARACTER
CHARACTER_REFERENCE
WORLD
LOCATION
SCENE
SHOT
IMAGE
VIDEO
AUDIO
VOICE
DIALOGUE_AUDIO
MUSIC
SFX
SUBTITLE
TRANSCRIPT
THUMBNAIL
PREVIEW
TIMELINE
RENDER
DOCUMENT
JSON
MODEL_OUTPUT
MASK
DEPTH
POSE
EMBEDDING
OTHER
```

Implementations MAY extend the enum through versioned contracts.

An asset type describes the **semantic role**, not merely the MIME type.

For example:

```text
assetType = VIDEO
mimeType  = video/mp4
```

and:

```text
assetType = CHARACTER_REFERENCE
mimeType  = image/png
```

are both valid.

---

# 5. Asset Status

Recommended lifecycle states:

```text
STAGING
UPLOADING
AVAILABLE
PROCESSING
QUARANTINED
CORRUPTED
ARCHIVED
DELETED
BLOCKED
```

Rules:

- `STAGING` MUST NOT be exposed as a production output.
- `UPLOADING` MUST NOT be consumed by workers.
- `AVAILABLE` means integrity checks have passed.
- `PROCESSING` means a derived/transform operation is active.
- `QUARANTINED` means security, integrity, license, or validation requires isolation.
- `CORRUPTED` MUST NOT be silently consumed.
- `ARCHIVED` remains recoverable according to retention policy.
- `DELETED` MUST not be physically referenced by active jobs.
- `BLOCKED` cannot be used by normal pipeline execution.

---

# 6. Logical Asset vs Physical Blob

## 6.1 Logical Asset

Contains domain meaning and relationships.

Examples:

```text
Character reference image
Shot video take 03
Final rendered episode
Dialogue WAV
Thumbnail
```

## 6.2 Blob

Contains bytes stored by a storage backend.

A Blob SHOULD contain:

```text
blobId
storageProvider
storageKey
contentHash
hashAlgorithm
sizeBytes
mimeType
createdAt
```

Multiple logical assets MAY reference the same immutable blob when deduplication is safe.

---

# 7. Content Hashing

Every production asset blob MUST have a cryptographic content hash.

Preferred algorithm:

```text
SHA-256
```

The system SHOULD support algorithm versioning for future migration.

Canonical representation:

```text
hashAlgorithm = SHA-256
hash = <hexadecimal digest>
```

The hash MUST be calculated from the actual stored bytes, not from metadata or a source filename.

Hash uses:

- integrity verification
- deduplication
- corruption detection
- cache identity
- reproducibility
- migration verification
- backup verification
- provenance auditing

A hash collision-resistant identifier MUST NOT be replaced by a filename-based identity.

---

# 8. Content-Addressable Storage

The storage layer SHOULD support content-addressable organization.

Example conceptual key:

```text
assets/<project>/<sha256-prefix>/<sha256>
```

The exact physical path is implementation-specific.

Domain code MUST use a storage abstraction rather than constructing physical paths directly.

Storage keys SHOULD avoid user-controlled raw filenames to reduce traversal and naming attacks.

---

# 9. Storage Abstraction

The domain/backend MUST define a storage interface similar to:

```text
put(input, options) -> BlobRef
get(blobRef) -> stream
head(blobRef) -> BlobMetadata
exists(blobRef) -> boolean
delete(blobRef) -> result
copy(source, destination) -> BlobRef
move(source, destination) -> BlobRef
verify(blobRef) -> IntegrityResult
createMultipartUpload(options) -> UploadSession
completeMultipartUpload(session) -> BlobRef
abortMultipartUpload(session) -> result
```

The interface MUST hide provider-specific APIs from domain logic.

---

# 10. Supported Storage Backends

The architecture SHOULD support:

1. Local filesystem
2. Mounted persistent volume
3. S3-compatible object storage
4. Cloud object storage adapters
5. Shared worker storage
6. Temporary local worker storage
7. Future CDN-backed delivery

Examples of implementation classes may include:

```text
LocalFilesystemStorage
S3CompatibleStorage
ObjectStorageAdapter
SharedVolumeStorage
MockStorage
```

No application layer may assume S3 or a local filesystem is always available.

---

# 11. Local-First Mode

Local-first mode MUST be a first-class deployment mode.

A minimal offline pipeline SHOULD work with:

```text
Android/API
   ↓
Local backend
   ↓
Local persistent storage
   ↓
Local/mock workers
```

The same logical Asset contract MUST work when storage later moves to object storage.

Offline mode MUST NOT invent fake successful assets. Mock assets must be explicitly marked as mock/deterministic outputs.

---

# 12. Android Boundary

Android MUST NOT directly manage provider-specific storage credentials.

Preferred flow:

```text
Android
  ↓
API upload/session request
  ↓
Backend authorization
  ↓
Upload endpoint or signed URL
  ↓
Storage
  ↓
Asset registration
  ↓
Integrity validation
  ↓
AVAILABLE
```

Android may cache thumbnails/previews locally, but production asset identity remains backend-controlled.

Large media MUST NOT be unnecessarily copied through Android memory.

---

# 13. Backend ↔ Worker Boundary

Workers MUST consume assets through an abstraction such as:

```text
AssetReference → StorageService → stream/local materialization
```

A worker MAY materialize a blob to local scratch storage when a model/tool requires a filesystem path.

The worker MUST NOT assume that the logical asset's storage key is a valid local path.

After execution:

```text
worker output
   ↓
atomic upload
   ↓
hash/probe
   ↓
asset registration
   ↓
provenance
   ↓
QC
```

---

# 14. Temporary, Staging, and Final Storage

Storage MUST distinguish at least:

```text
staging/
temp/
assets/
archive/
quarantine/
```

Temporary data MUST have a TTL.

Staging data MUST be promoted only after validation.

A production asset MUST NOT be represented merely by a path inside a temporary directory.

---

# 15. Atomic Writes

Asset publication MUST be atomic from the application's perspective.

Recommended sequence:

```text
write temporary blob
      ↓
flush/close
      ↓
calculate hash
      ↓
validate size/type
      ↓
media probe if applicable
      ↓
move/copy to immutable storage
      ↓
commit DB Asset + Blob record
      ↓
AVAILABLE
```

A failed write MUST NOT leave a falsely `AVAILABLE` asset.

Database and storage operations MUST have explicit recovery logic because they cannot always participate in one physical transaction.

---

# 16. Uploads

The API SHOULD support:

- direct small uploads
- multipart uploads
- resumable uploads
- signed upload URLs where appropriate
- upload session IDs
- client-provided expected hash
- server-side verification

For large files:

```text
create upload session
→ upload chunks
→ resume failed chunks
→ complete
→ verify hash
→ register Asset
```

Partial uploads MUST NOT become production assets.

Upload sessions MUST expire.

---

# 17. Download and Delivery

Download modes may include:

```text
stream through API
signed URL
local file endpoint
worker-internal access
```

Large immutable media SHOULD use signed URLs or equivalent controlled direct delivery when appropriate.

Signed URLs MUST:

- expire
- be scoped to the intended asset/object
- respect project authorization
- not expose storage credentials

---

# 18. Metadata and Media Probing

The system MUST distinguish declared metadata from probed metadata.

For media, the backend/worker SHOULD inspect:

```text
MIME type
container
codec
duration
width
height
frame rate
bit rate
sample rate
channels
pixel format
frame count when available
audio/video stream count
```

FFprobe or an equivalent implementation may be used behind an abstraction.

Client-provided MIME type MUST NOT be trusted as the sole validation mechanism.

---

# 19. File Type and Security Validation

The system MUST validate content before making it available to production jobs.

Validation SHOULD include:

1. extension sanity
2. MIME sniffing/probing
3. byte-level parse where practical
4. size limits
5. decompression limits
6. malware/security scanning where deployed
7. media decoder safety
8. project authorization

User-controlled filenames MUST be treated as display metadata, not executable paths.

Path traversal such as `../` MUST never reach a storage path constructor.

---

# 20. Provenance

Every generated production asset MUST retain provenance sufficient to answer:

> How was this asset produced, from which inputs, using which job, provider, model, parameters, and source assets?

Minimum provenance SHOULD include:

```text
assetId
jobId
projectId
provider
providerVersion
model
modelVersion
prompt
negativePrompt
seed
parameters
referenceAssetIds
sourceAssetIds
parentAssetId
workflowId
workflowVersion
workerId
createdAt
```

Additional fields may include:

```text
runtime
hardware
CUDA/ROCm version
softwareVersion
gitCommit
requestId
userId
licenseSnapshot
cost
latency
qualityMetrics
```

Secrets MUST NEVER be stored in provenance.

API keys, bearer tokens, credentials, signed URLs, and private headers MUST be excluded or redacted.

---

# 21. Provenance Immutability

Once an asset becomes `AVAILABLE`, its historical provenance MUST be append-only or immutable.

If a correction is required:

```text
old Asset
   ↓
new Asset version
```

Do not silently rewrite generation history.

Corrections to descriptive metadata MAY be allowed if audit history is retained.

---

# 22. Derived Assets and Lineage

Derived assets MUST retain explicit lineage.

Examples:

```text
source image
   ↓
upscaled image
   ↓
video generation
   ↓
lipsync video
   ↓
color/technical processing
   ↓
final shot
```

The system SHOULD represent lineage as a directed acyclic graph.

Each derived asset SHOULD reference:

```text
sourceAssetIds[]
parentAssetId
transformation/jobId
```

Cycles MUST be rejected unless explicitly modeled for a non-lineage relationship.

---

# 23. Asset Versioning

Versioning MUST be explicit.

Recommended conceptual model:

```text
logicalAssetId
versionNumber
blobId
createdAt
supersedesAssetVersionId
```

An immutable generated take should normally receive a new version/take rather than overwriting the original bytes.

For example:

```text
Shot 12
 ├── Take 1
 ├── Take 2
 └── Take 3
```

Best Take selection references one of these immutable outputs.

---

# 24. Deduplication

Deduplication MAY occur when:

```text
same content hash
same compatible storage semantics
same integrity status
```

Deduplication MUST NOT destroy logical asset identity.

Two assets can be different logical objects while sharing one immutable blob.

The storage layer MUST use reference tracking before deleting a deduplicated blob.

---

# 25. QC Integration

Asset availability does not imply asset quality.

The pipeline is:

```text
Asset created
   ↓
Integrity validation
   ↓
Technical probe
   ↓
Media QC
   ↓
Continuity QC
   ↓
Semantic QC
   ↓
QC result
```

A failed QC asset MAY remain stored for diagnostics but MUST NOT be treated as a valid final output.

QC records MUST reference the relevant Asset and, where applicable, GenerationJob.

---

# 26. Best Take Integration

Best Take selection MUST reference immutable asset versions.

Example:

```text
Shot
 ├── video_take_01
 ├── video_take_02
 ├── video_take_03 ← BEST TAKE
 └── video_take_04
```

Selecting a Best Take MUST NOT copy or mutate the media unnecessarily.

It should create a logical selection/reference.

---

# 27. Timeline Integration

Timeline clips MUST reference Asset IDs or immutable asset versions, not arbitrary filesystem paths.

Example:

```text
TimelineClip
  assetId
  assetVersion
  startMs
  durationMs
  sourceInMs
  sourceOutMs
```

The renderer resolves Asset references through the storage abstraction.

---

# 28. Rendering Integration

Render jobs MUST treat source assets as immutable inputs.

A render SHOULD create:

```text
RenderJob
   ↓
output staging blob
   ↓
integrity validation
   ↓
media probe
   ↓
QC
   ↓
final Render Asset
```

A render job MUST NOT mark itself completed merely because FFmpeg returned exit code 0.

The output file MUST exist, be readable, pass required validation, and satisfy required QC.

---

# 29. Thumbnails and Previews

Large media SHOULD have derived preview assets.

Typical derivatives:

```text
original video
 ├── thumbnail.jpg
 ├── contact_sheet.jpg
 └── preview.mp4
```

Preview assets MUST retain lineage to their source asset.

Thumbnail generation SHOULD be asynchronous for large media.

A missing optional preview MUST NOT make the original production asset invalid unless the contract explicitly requires it.

---

# 30. Naming and Paths

Human-readable names are metadata only.

Storage keys SHOULD be generated by the system.

Do not use:

```text
../../file.mp4
user-input-as-a-directory/file.mp4
```

Prefer opaque/generated keys.

A logical naming convention may be exposed to users:

```text
Project / Episode / Scene / Shot / Take
```

but physical storage remains implementation-controlled.

---

# 31. Project Isolation

Every asset MUST belong to a project or another explicitly authorized tenant boundary.

All access paths MUST enforce:

```text
authenticated user
→ project membership
→ asset authorization
→ operation authorization
```

An asset ID alone MUST NOT grant access.

Cross-project source references MUST be explicitly authorized and auditable.

---

# 32. Access Control

Operations SHOULD be separated:

```text
asset.read
asset.create
asset.update_metadata
asset.delete
asset.download
asset.publish
asset.archive
asset.restore
asset.admin
```

Workers should receive only the permissions necessary for their jobs.

---

# 33. Secrets

Storage credentials MUST live in environment/configuration/secret management systems.

Never store:

- access keys
- secret keys
- API tokens
- signed URLs
- private credentials

inside:

- Asset metadata
- Provenance JSON
- Git
- logs
- database audit payloads

unless explicitly encrypted and required by an approved design.

---

# 34. Quotas

The storage subsystem SHOULD support limits by:

```text
project
user
workspace
storage class
file count
single file size
active upload size
```

Quota checks SHOULD happen before expensive operations where possible.

Workers SHOULD be prevented from exhausting shared disk space.

---

# 35. Retention and Garbage Collection

Assets MUST have lifecycle policies.

Possible classes:

```text
TEMP
STAGING
ACTIVE
ARCHIVE
DELETE_PENDING
```

Garbage collection MUST be reference-aware.

A blob is eligible for deletion only when:

```text
no live Asset references it
AND
no active job references it
AND
no timeline/render/publish operation requires it
AND
retention policy permits deletion
```

Failed/abandoned temporary files SHOULD be collected automatically.

---

# 36. Archive

Archiving SHOULD preserve:

- asset identity
- blob integrity
- provenance
- lineage
- metadata
- audit history

Restoration MUST revalidate integrity before returning an asset to `AVAILABLE`.

---

# 37. Corruption Handling

If hash verification fails:

```text
Asset → CORRUPTED
```

Then:

1. stop normal consumption
2. record integrity failure
3. emit asset event
4. identify affected jobs/outputs
5. attempt recovery from replica/backup when configured
6. rerun generation only when recovery is impossible or intentionally selected

Corruption MUST NOT be silently ignored.

---

# 38. Backup and Recovery

Backups SHOULD cover:

```text
Database metadata
Asset blobs
Provenance
Storage configuration
Critical indexes/manifests
```

Database-only backup is insufficient for production media.

Blob-only backup is insufficient because logical relationships and provenance may be lost.

Recovery testing MUST verify:

```text
restore DB
→ restore blobs
→ verify hashes
→ restore references
→ run integrity checks
```

---

# 39. Migration

Storage migration MUST be provider-independent.

Example:

```text
LocalFilesystem
      ↓
Migration Worker
      ↓
S3-Compatible Storage
      ↓
hash verification
      ↓
metadata update
```

The migration MUST preserve logical Asset IDs and provenance.

A migration SHOULD be resumable and idempotent.

---

# 40. Eventing

Important asset events SHOULD include:

```text
ASSET_CREATED
ASSET_UPLOADING
ASSET_AVAILABLE
ASSET_UPDATED
ASSET_DERIVED
ASSET_QC_STARTED
ASSET_QC_COMPLETED
ASSET_CORRUPTED
ASSET_ARCHIVED
ASSET_RESTORED
ASSET_DELETE_REQUESTED
ASSET_DELETED
ASSET_DOWNLOAD_STARTED
ASSET_DOWNLOAD_COMPLETED
```

Events SHOULD include:

```text
eventId
assetId
projectId
timestamp
actor/request/job context
schemaVersion
```

Consumers MUST tolerate duplicate and out-of-order events.

---

# 41. Observability

The storage subsystem SHOULD expose metrics for:

```text
upload_count
upload_bytes
upload_failures
download_count
download_bytes
storage_used_bytes
storage_free_bytes
hash_verification_failures
corruption_count
gc_bytes_reclaimed
upload_duration
probe_duration
signed_url_generation_failures
```

Logs MUST contain useful correlation identifiers but no secrets.

---

# 42. Replit Boundary

Replit/backend development environments may provide API/orchestration/storage for development and lightweight execution.

Heavy GPU workers may run elsewhere.

Therefore:

```text
Replit Backend
   ↓
Persistent Object/Shared Storage
   ↓
GPU Worker
```

The design MUST NOT depend on a worker's ephemeral local filesystem surviving worker termination.

Worker scratch space is temporary.

Production asset persistence belongs to the storage subsystem.

---

# 43. Worker Scratch Storage

Workers SHOULD use isolated scratch directories such as:

```text
/tmp/ai-content-factory/<jobId>/
```

Rules:

- one job must not accidentally consume another job's files
- cleanup must occur after success/failure/cancellation
- scratch files have TTL
- scratch files are not production Assets
- paths are never persisted as durable asset identity

---

# 44. Model and Provider Provenance

For AI-generated outputs, provenance SHOULD capture the exact model identity from Model Registry.

At minimum:

```text
providerId
modelId
modelVersion
runtime
parameters
seed
prompt
negativePrompt
referenceAssetIds
```

If the model version is unknown, provenance MUST say so rather than fabricate a version.

---

# 45. Workflow Provenance

When a workflow contains multiple transformations, provenance SHOULD capture the workflow graph.

Example:

```text
Prompt
 ↓
Image Model
 ↓
Image
 ↓
Video Model
 ↓
Video
 ↓
LipSync
 ↓
Final Shot
```

Each transformation should be traceable to its job and input assets.

---

# 46. License and Rights Metadata

Assets MAY carry rights metadata such as:

```text
licenseStatus
licenseId
sourceUrl
creator
attributionRequired
commercialUseAllowed
modificationAllowed
redistributionAllowed
```

The canonical license statuses are:

```text
VERIFIED
UNKNOWN
RESTRICTED
BLOCKED
```

`UNKNOWN` MUST NOT be treated as verified-safe for a production policy that requires verified licensing.

License evidence SHOULD be snapshotted into provenance when legally appropriate.

---

# 47. API Requirements

The API MUST expose logical Asset resources, not raw storage internals.

Recommended endpoints:

```text
GET    /api/v1/assets
POST   /api/v1/assets
GET    /api/v1/assets/{assetId}
PATCH  /api/v1/assets/{assetId}
DELETE /api/v1/assets/{assetId}
GET    /api/v1/assets/{assetId}/download
POST   /api/v1/assets/{assetId}/verify
GET    /api/v1/assets/{assetId}/provenance
GET    /api/v1/assets/{assetId}/lineage
GET    /api/v1/assets/{assetId}/versions
POST   /api/v1/assets/upload-sessions
POST   /api/v1/assets/upload-sessions/{id}/complete
```

Exact endpoint shape must remain consistent with `API_SPECIFICATION.md`.

---

# 48. Idempotency

Asset registration and upload completion SHOULD support idempotency keys.

Repeated completion requests MUST NOT create duplicate logical assets accidentally.

The same content may deduplicate physically while retaining explicit logical identity rules.

---

# 49. Concurrency

The system MUST handle concurrent operations safely.

Examples:

- two workers producing the same derivative
- deletion during download
- archival during QC
- migration during rendering
- repeated upload completion

Use optimistic locking, leases, database constraints, or equivalent mechanisms.

An asset referenced by an active job MUST NOT be physically deleted.

---

# 50. Asset State vs Job State

Asset state and Job state are separate.

Example:

```text
Job = COMPLETED
Asset = CORRUPTED
```

is valid as a historical record but the overall pipeline MUST treat the output as unusable.

Likewise:

```text
Job = RUNNING
Asset = STAGING
```

is normal.

A completed job requires validated outputs according to the Job contract.

---

# 51. Storage Classes

The implementation MAY support:

```text
HOT
WARM
COLD
ARCHIVE
TEMP
```

Routing between classes should be policy-driven.

The domain must not hard-code provider-specific storage tiers.

---

# 52. Asset Manifests

For large workflows, an immutable manifest SHOULD describe the exact asset set required for a render/export.

Example:

```text
manifestId
projectId
assetIds[]
hashes[]
createdAt
schemaVersion
```

A renderer can verify the manifest before starting an expensive render.

---

# 53. Reproducibility

Where deterministic generation is possible, the system SHOULD preserve:

```text
seed
model version
prompt
parameters
reference hashes
workflow version
software version
```

A provenance record must describe what actually happened, not what the system expected to happen.

---

# 54. Offline / Mock Storage

CI and deterministic tests SHOULD use `MockStorage` or an equivalent implementation.

Mock behavior MUST support:

- put/get
- hash verification
- metadata
- lineage references
- deletion/reference checks
- deterministic failure injection

Mock storage MUST NOT bypass the same logical Asset contract used by production.

---

# 55. Testing Requirements

## Unit Tests

Test:

- hash calculation
- MIME/type validation
- path/key generation
- metadata extraction
- provenance serialization
- lineage validation
- deduplication
- quota checks
- retention rules
- state transitions

## Integration Tests

Test:

- local storage
- object storage adapter
- upload session lifecycle
- resumable uploads
- signed delivery
- worker materialization
- corruption detection
- migration
- garbage collection

## Contract Tests

Verify Android/API/backend/worker agreement for:

- Asset DTOs
- upload sessions
- download references
- provenance
- lineage
- asset events

## E2E Tests

Run the full Golden pipeline with deterministic mock storage and workers.

---

# 56. Golden Asset Pipeline

The canonical asset lifecycle is:

```text
Project
 ↓
Episode
 ↓
Scene
 ↓
Shot
 ↓
GenerationJob
 ↓
Worker
 ↓
Staging Blob
 ↓
Hash
 ↓
Probe
 ↓
Asset Registration
 ↓
Provenance
 ↓
QC
 ↓
Best Take
 ↓
Timeline
 ↓
Render
 ↓
Final Asset
 ↓
Publish
```

Every stage must preserve traceability.

---

# 57. Failure Scenarios

The implementation MUST define behavior for at least:

1. upload interrupted
2. storage unavailable
3. disk full
4. hash mismatch
5. corrupted media
6. unsupported MIME
7. worker crash during output
8. duplicate completion request
9. asset deleted while job is running
10. object storage timeout
11. migration interrupted
12. backup restore mismatch
13. signed URL expiration
14. orphaned blob
15. orphaned Asset metadata
16. QC failure
17. provider output with invalid media
18. project authorization failure

No failure should result in a false `AVAILABLE` state.

---

# 58. Implementation Order

Recommended implementation sequence:

### Phase 1 — Storage Foundation

- Blob abstraction
- Asset repository
- local filesystem adapter
- SHA-256 hashing
- metadata persistence

### Phase 2 — Upload/Download

- upload sessions
- atomic staging
- resumable uploads
- download abstraction
- authorization

### Phase 3 — Provenance

- provenance model
- job/provider/model linkage
- sourceAssetIds
- lineage graph
- versioning

### Phase 4 — Media Intelligence

- media probing
- thumbnails
- previews
- validation
- corruption detection

### Phase 5 — Pipeline Integration

- workers
- QC
- Best Take
- Timeline
- Renderer

### Phase 6 — Production Storage

- S3-compatible adapter
- signed URLs
- quotas
- lifecycle
- archive
- backup/recovery

### Phase 7 — Reliability

- migration
- garbage collection
- observability
- failure injection
- contract tests
- Golden E2E

---

# 59. Non-Negotiable Rules

1. Asset and Blob are separate abstractions.
2. Production blobs MUST be integrity-verifiable.
3. SHA-256 or an approved equivalent MUST identify content integrity.
4. Domain code MUST NOT depend on filesystem paths.
5. Temporary files MUST NOT be treated as durable Assets.
6. Generated outputs MUST retain provenance.
7. Derived assets MUST retain lineage.
8. Production asset provenance MUST NOT be silently rewritten.
9. Asset IDs MUST NOT grant access without authorization.
10. Storage credentials MUST NOT enter Git, logs, metadata, or provenance.
11. Partial uploads MUST NOT become available production assets.
12. Corrupted assets MUST NOT be silently consumed.
13. Deduplication MUST NOT destroy logical asset identity.
14. Physical deletion MUST be reference-aware.
15. Timeline and Render MUST reference logical Assets, not arbitrary paths.
16. QC status and Asset availability are separate concepts.
17. Mock storage MUST follow the same logical contracts as production storage.
18. Heavy workers MUST NOT depend on ephemeral local storage for durable outputs.
19. Storage migration MUST preserve logical IDs and provenance.
20. No job may be considered successfully complete solely because a file was written.

---

# 60. Definition of Done

The Asset/Storage subsystem is considered complete only when:

- Asset and Blob models exist.
- Storage abstraction exists.
- Local storage implementation works.
- Content hashing works.
- Atomic writes work.
- Upload lifecycle is persistent and resumable where required.
- Download authorization is enforced.
- Media metadata is validated/probed.
- Provenance is persisted.
- Derived lineage is persisted.
- Versioning is explicit.
- Deduplication is safe.
- QC linkage works.
- Best Take linkage works.
- Timeline linkage works.
- Render linkage works.
- Retention and garbage collection are reference-aware.
- Corruption is detectable.
- Backup/recovery strategy is documented and tested.
- Project isolation is enforced.
- No secrets are stored in assets/provenance/logs.
- Mock storage supports deterministic CI.
- Contract tests pass.
- Golden E2E passes.
- Existing tests still pass.
- Build succeeds.
- No fake production success paths remain.
- Documentation matches implementation.

---

# 61. Final Architecture Contract

The authoritative mental model is:

```text
                 ┌──────────────────────┐
                 │       Android        │
                 └──────────┬───────────┘
                            │ API
                            ▼
                 ┌──────────────────────┐
                 │ Backend / Orchestrator│
                 └──────────┬───────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
        ┌───────────────┐       ┌───────────────┐
        │ Asset Service │       │ Job / Queue    │
        └───────┬───────┘       └───────┬───────┘
                │                       │
                ▼                       ▼
        ┌───────────────┐       ┌───────────────┐
        │ Blob Storage  │◄──────│ Workers        │
        └───────┬───────┘       └───────────────┘
                │
                ▼
        ┌───────────────┐
        │ Hash / Probe  │
        │ Provenance    │
        │ Lineage       │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │ QC / BestTake │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │ Timeline      │
        │ Renderer      │
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │ Final Asset   │
        └───────────────┘
```

The Asset subsystem is therefore not merely a file-upload feature. It is the durable evidence layer connecting generation, storage, provenance, quality, editing, rendering, publishing, recovery, and reproducibility.

**End of Specification — Version 1.0**
