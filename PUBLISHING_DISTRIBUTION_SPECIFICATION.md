# PUBLISHING & DISTRIBUTION SPECIFICATION

**Version:** 1.0  
**Status:** Normative Engineering Specification  
**Scope:** Final assets → publishing jobs → platform adapters → upload → metadata → thumbnails → captions → scheduling → publish verification → analytics

---

## 1. Purpose

This document defines the production contract for distributing completed media from AI Content Factory to external publishing platforms.

The publishing subsystem MUST be separated from content generation, rendering, and Android UI. A successful render is not a successful publication. Publication MUST be represented by a persistent `PublishingJob`, executed through provider/platform adapters, verified after upload, and linked to immutable source assets and metadata.

Canonical flow:

```text
Final Asset
  → Publication Plan
  → Publishing Job
  → Preflight/QC
  → Platform Adapter
  → Upload
  → Metadata
  → Thumbnail
  → Captions
  → Scheduling
  → Publish
  → Verification
  → Analytics
```

---

## 2. Non-Negotiable Rules

1. Android MUST NOT upload directly to social platforms.
2. Publishing MUST run through backend/orchestrator/worker boundaries.
3. Every publication MUST reference an immutable final asset or render snapshot.
4. A rendered file MUST pass required QC before publishing.
5. Platform credentials MUST never be stored in source code, logs, job payloads, or Git.
6. Publishing MUST be idempotent.
7. A network success response MUST NOT alone mark a publication `PUBLISHED`.
8. Every platform integration MUST implement an adapter interface; business logic MUST NOT be hard-coded for one platform.
9. Platform-specific metadata MUST be normalized from a common publication model.
10. Scheduling MUST use explicit timezone information and UTC persistence.
11. Retries MUST distinguish temporary transport failures from permanent platform rejection.
12. A publication failure MUST preserve the job, request, provider response classification, and retry history.
13. External platform identifiers MUST be persisted after creation.
14. Analytics MUST remain logically separate from publication state.
15. Unsupported platform capabilities MUST fail explicitly rather than silently degrading.
16. Secrets MUST be resolved at execution time through a secret/credential boundary.
17. Deleting or replacing a source asset MUST NOT silently invalidate an already verified publication.
18. Publishing adapters MUST be testable in deterministic mock mode without real platform credentials.

---

## 3. Domain Model

### 3.1 Publication Plan

Represents the user's intent to distribute one content item to one or more platforms.

Minimum fields:

```text
id
projectId
sourceAssetId
renderJobId
contentVersion
status
platformTargets[]
metadataProfileId
captionProfileId
thumbnailAssetId
scheduledAt
scheduledTimezone
createdAt
updatedAt
```

A publication plan MAY contain multiple platform targets, but each actual platform execution MUST have its own persistent job/state.

### 3.2 Publishing Job

Minimum fields:

```text
id
projectId
publicationPlanId
platform
accountId
sourceAssetId
renderSnapshotId
status
attempt
maxAttempts
idempotencyKey
externalPublicationId
requestHash
scheduledAt
startedAt
completedAt
verifiedAt
updatedAt
errorCode
errorMessage
platformErrorCode
platformResponseRef
createdAt
```

### 3.3 Publishing Status

Recommended state machine:

```text
PENDING
  → PREFLIGHT
  → QUEUED
  → RUNNING
  → UPLOADING
  → PROCESSING
  → SCHEDULED
  → PUBLISHED
  → VERIFIED
```

Failure/cancellation states:

```text
RETRYING
FAILED
CANCELLED
BLOCKED
```

`VERIFIED` is the terminal success state for the platform publication workflow.

A platform may expose an intermediate processing state after upload. The adapter MUST poll, receive callbacks, or otherwise verify the external state before reporting success.

---

## 4. Source Asset and Render Snapshot

Publishing MUST consume a stable artifact.

Before publication begins, the system MUST capture:

- asset ID;
- content hash;
- MIME type;
- byte size;
- duration;
- resolution;
- frame rate;
- audio properties;
- subtitle/caption assets where applicable;
- render profile;
- timeline version;
- QC result IDs;
- provenance references.

The snapshot prevents a later timeline edit or asset replacement from changing what an existing publishing job intended to publish.

---

## 5. Preflight Gate

Every publishing job MUST pass preflight.

Preflight checks SHOULD include:

- source asset exists;
- asset integrity/hash valid;
- asset is readable;
- final render completed;
- required QC passed;
- no blocking QC findings;
- platform supports the selected media format;
- duration is within platform limits;
- dimensions/aspect ratio are supported;
- codec/container is supported;
- audio configuration is supported;
- file size is within platform limits;
- captions satisfy platform requirements;
- thumbnail exists when required;
- title/description/caption metadata satisfies limits;
- account authorization is available;
- requested operation is permitted by the connected account;
- license/policy gate is passed;
- scheduled time is valid.

Failure MUST prevent upload and produce a structured error.

---

## 6. Platform Adapter Architecture

The publishing core MUST depend on an abstraction similar to:

```text
PublishingAdapter
  ├── capabilities()
  ├── validate(request)
  ├── authenticate(account)
  ├── createUploadSession(request)
  ├── uploadMedia(session, asset)
  ├── applyMetadata(publication, metadata)
  ├── applyThumbnail(publication, thumbnail)
  ├── applyCaptions(publication, captions)
  ├── schedule(publication, schedule)
  ├── publish(publication)
  ├── getStatus(externalId)
  ├── verify(publication)
  ├── cancel(publication)
  └── delete(publication)
```

Adapters MUST NOT own project/business state. They translate the normalized publication contract into platform-specific API operations.

---

## 7. Platform Capability Matrix

Each adapter MUST expose machine-readable capabilities.

Example:

```text
videoUpload
imageUpload
shortVideo
longVideo
scheduledPublish
captionUpload
thumbnailUpload
customThumbnail
title
description
hashtags
tags
location
privacyControls
playlist/collection
statusPolling
webhookEvents
postUpdate
postDelete
analytics
```

The orchestrator MUST validate requested features against capabilities before dispatch.

---

## 8. Credentials and Account Connections

Account credentials MUST be represented by references, never raw secrets.

Conceptual model:

```text
PlatformAccount
  id
  projectId
  platform
  externalAccountId
  displayName
  credentialRef
  scopes
  status
  expiresAt
  lastValidatedAt
  createdAt
  updatedAt
```

Secrets SHOULD be stored in an appropriate secret manager or encrypted credential store.

Logs MUST redact:

- access tokens;
- refresh tokens;
- cookies;
- authorization codes;
- client secrets;
- signed upload URLs when sensitive;
- private account identifiers where required.

Token refresh MUST be centralized rather than duplicated in individual business workflows.

---

## 9. Metadata Model

Use a platform-neutral metadata model first.

Recommended fields:

```text
title
description
caption
hashtags
tags
language
category
privacy
location
contentWarnings
attribution
license
playlist/collection
seriesTitle
seasonNumber
episodeNumber
publishTimezone
```

Then map to platform-specific fields.

The system MUST preserve the normalized metadata used for the publication request, including a version/hash so the exact submitted metadata can be audited.

---

## 10. Captions and Subtitles

Captions are separate assets or logical resources and MUST have provenance.

Supported representations MAY include:

- WebVTT;
- SRT;
- TTML;
- platform-native caption structures;
- burned-in subtitles as a fallback only when explicitly selected.

The publishing pipeline MUST distinguish:

```text
subtitle asset
caption track
burned-in subtitle
transcript
```

Caption timing SHOULD be validated against the final render version. A caption track generated against an earlier render MUST NOT automatically be reused if timeline timing changed.

---

## 11. Thumbnail Pipeline

Thumbnail generation is a first-class job, not an ad-hoc upload.

Flow:

```text
Final/Proxy Asset
  → Candidate Frames
  → Thumbnail Generation
  → Thumbnail QC
  → Selection
  → Platform Adaptation
  → Upload
```

Thumbnail provenance MUST reference:

- source asset;
- timestamp/frame;
- generation method/model if AI-generated;
- crop/transform;
- output hash;
- selected publication job.

Platform-specific dimensions and file-size requirements MUST be checked by the adapter capability layer.

---

## 12. Scheduling

Scheduling MUST persist timestamps in UTC and retain the user's intended timezone.

Required information:

```text
scheduledAtUtc
scheduledTimezone
scheduleSource
```

The scheduler MUST handle daylight-saving transitions where applicable.

A publication scheduled for the future MUST NOT be treated as `PUBLISHED` merely because the scheduling request was accepted.

Recommended flow:

```text
PENDING → QUEUED → SCHEDULED → platform processing → PUBLISHED → VERIFIED
```

If the platform cannot schedule natively, the system MAY use its own scheduler to execute at the requested time, subject to platform policy and account capabilities.

---

## 13. Upload Strategy

Adapters SHOULD support resumable/chunked uploads where the platform permits them.

Large media MUST NOT be loaded entirely into Android memory.

Upload sessions SHOULD track:

```text
sessionId
sourceAssetId
bytesTotal
bytesUploaded
chunkSize
uploadUrlRef
expiresAt
checksum
```

Partial upload state MUST be recoverable when the external platform supports resume.

Expired upload sessions MUST be recreated safely.

---

## 14. Idempotency and Duplicate Prevention

Every publishing operation MUST have a deterministic idempotency boundary.

A recommended key is derived from:

```text
projectId + platform + accountId + sourceAssetHash + metadataHash + scheduleHash
```

The system MUST prevent accidental duplicate publication after:

- worker crash;
- timeout after remote acceptance;
- lost response;
- process restart;
- scheduler restart;
- retry;
- network interruption.

When remote APIs do not provide native idempotency, the adapter MUST use persisted request hashes and external IDs/status reconciliation.

---

## 15. Retry and Failure Classification

### Retryable

Examples:

- temporary network failure;
- HTTP 429/rate limiting;
- transient 5xx response;
- expired upload session;
- temporary provider processing failure;
- worker restart after a lease expires.

### Non-Retryable

Examples:

- invalid credentials requiring user action;
- insufficient permissions;
- unsupported media format;
- content policy rejection;
- invalid metadata;
- permanently invalid account state;
- platform feature unavailable;
- asset corruption;
- missing required thumbnail/caption.

Retry MUST use bounded exponential backoff with jitter and MUST respect platform rate limits.

---

## 16. Remote Verification

Verification is mandatory.

The adapter MUST confirm, as far as the platform permits:

- external publication ID exists;
- remote status is successful;
- target account matches expected account;
- media corresponds to the intended publication;
- scheduled/published state is correct;
- metadata is present where queryable;
- thumbnail/captions are present where queryable.

Verification SHOULD use external IDs plus persisted request hashes and returned metadata.

If the platform only exposes eventual consistency, the job remains `PROCESSING` until a bounded verification policy is exhausted.

---

## 17. Webhooks and Polling

Adapters MAY support both webhooks and polling.

Webhook processing MUST be:

- authenticated where possible;
- idempotent;
- replay-safe;
- tolerant of duplicate events;
- tolerant of out-of-order events.

Polling MUST use bounded intervals and stop after a configurable timeout.

The persisted event model SHOULD contain:

```text
eventId
platform
externalPublicationId
eventType
receivedAt
payloadHash
processedAt
processingStatus
```

Raw sensitive payloads MUST be minimized and protected.

---

## 18. Publishing Events

Recommended internal events:

```text
PUBLISHING_JOB_CREATED
PUBLISHING_PREFLIGHT_STARTED
PUBLISHING_PREFLIGHT_FAILED
PUBLISHING_STARTED
PUBLISHING_UPLOAD_PROGRESS
PUBLISHING_UPLOAD_COMPLETED
PUBLISHING_PROCESSING
PUBLISHING_SCHEDULED
PUBLISHING_SUCCEEDED
PUBLISHING_VERIFIED
PUBLISHING_RETRYING
PUBLISHING_FAILED
PUBLISHING_CANCELLED
```

Consumers MUST tolerate duplicate and out-of-order events.

---

## 19. Analytics Boundary

Publication state and analytics state are separate concerns.

A successful publication creates an external identity that analytics can later query.

Conceptual flow:

```text
Publishing Verification
       ↓
External Publication ID
       ↓
Analytics Collection Job
       ↓
Normalized Metrics
       ↓
AnalyticsRecord
       ↓
Learning / Optimization
```

Analytics MUST NOT mutate historical publication facts.

Recommended normalized metrics include:

```text
views
impressions
likes
comments
shares
saves
watchTime
averageViewDuration
completionRate
followersGained
clicks
engagementRate
collectedAt
```

Platform-specific metrics MAY be retained separately.

---

## 20. Analytics Collection Jobs

Analytics collection SHOULD be asynchronous.

Recommended job types:

```text
ANALYTICS_SYNC
PUBLICATION_STATUS_SYNC
ACCOUNT_STATUS_SYNC
```

Collection MUST support incremental synchronization and rate limiting.

Historical records SHOULD be append-oriented or versioned so changes in platform-reported values remain auditable.

---

## 21. Security and Project Isolation

Every publication resource MUST be scoped to a project/account authorization boundary.

The system MUST verify:

```text
authenticated user
  → project membership
  → publication ownership
  → platform account ownership/access
  → source asset authorization
```

Cross-project publication MUST be impossible by default.

Credentials MUST be scoped to the minimum platform permissions necessary.

Audit events SHOULD record sensitive administrative actions without recording secrets.

---

## 22. Content Policy and Licensing Gate

Before upload, the publishing pipeline SHOULD evaluate applicable policy/license constraints.

Examples:

- blocked asset license status;
- restricted source material;
- missing attribution;
- platform content restrictions;
- age/content classification;
- music licensing requirements;
- third-party media restrictions.

`UNKNOWN` license status MUST NOT be silently treated as verified.

A policy blocker MUST prevent publication unless an explicit authorized override mechanism exists.

---

## 23. Batch Publishing

The system SHOULD support publishing one finalized episode to multiple platforms.

Example:

```text
Episode Final Asset
 ├─ Platform A Publishing Job
 ├─ Platform B Publishing Job
 ├─ Platform C Publishing Job
 └─ Platform D Publishing Job
```

Jobs MUST remain independently retryable and independently verifiable.

A failure on one platform MUST NOT automatically fail successful publications on other platforms.

Batch orchestration MAY provide an aggregate status:

```text
ALL_PENDING
PARTIAL_SUCCESS
ALL_SUCCEEDED
PARTIAL_FAILURE
ALL_FAILED
```

---

## 24. Rate Limits and Backpressure

The scheduler MUST account for platform rate limits.

Recommended controls:

- per-platform concurrency;
- per-account concurrency;
- request quotas;
- upload bandwidth limits;
- retry budgets;
- API call budgets;
- global worker capacity.

Rate limiting MUST integrate with the queue/scheduler specification rather than creating an independent hidden queue.

---

## 25. Cancellation

Cancellation behavior depends on platform capability.

Possible outcomes:

```text
CANCELLED_BEFORE_UPLOAD
CANCELLED_DURING_UPLOAD
REMOTE_UPLOAD_CANNOT_BE_CANCELLED
REMOTE_PUBLICATION_CANCELLED
REMOTE_PUBLICATION_REQUIRES_DELETE
```

The system MUST report actual external state rather than claiming cancellation when the remote platform has already accepted the publication.

---

## 26. Observability

Every publishing operation MUST be traceable using:

- request ID;
- publishing job ID;
- project ID;
- publication plan ID;
- platform;
- account ID reference;
- external publication ID;
- attempt number;
- adapter version;
- duration;
- final status;
- structured error classification.

Metrics SHOULD include:

```text
publish_success_rate
publish_failure_rate
verification_success_rate
upload_duration
processing_duration
queue_wait_duration
retry_count
rate_limit_count
platform_error_count
bytes_uploaded
cost_if_applicable
```

No secret or token may appear in telemetry.

---

## 27. API Contract

Publishing APIs MUST follow `API_SPECIFICATION.md`.

Recommended endpoints:

```text
POST   /api/v1/projects/{projectId}/publications
GET    /api/v1/projects/{projectId}/publications
GET    /api/v1/publications/{publicationId}
POST   /api/v1/publications/{publicationId}/validate
POST   /api/v1/publications/{publicationId}/publish
POST   /api/v1/publications/{publicationId}/schedule
POST   /api/v1/publications/{publicationId}/cancel
POST   /api/v1/publications/{publicationId}/retry
POST   /api/v1/publications/{publicationId}/verify
GET    /api/v1/publications/{publicationId}/events
GET    /api/v1/projects/{projectId}/platform-accounts
POST   /api/v1/projects/{projectId}/platform-accounts
DELETE /api/v1/platform-accounts/{accountId}
GET    /api/v1/projects/{projectId}/analytics
```

Long-running actions SHOULD return `202 Accepted` with a job reference.

Idempotency keys are REQUIRED for publish/schedule actions where duplicate execution could create an external side effect.

---

## 28. Database Requirements

The database MUST persist at minimum:

```text
publication_plans
publishing_jobs
platform_accounts
publishing_events
publication_metadata_versions
publication_captions
publication_thumbnails
analytics_records
```

Foreign keys SHOULD link publications to:

- projects;
- source assets;
- render jobs/snapshots;
- metadata versions;
- thumbnail assets;
- caption assets;
- account connections.

Indexes SHOULD cover:

```text
(project_id, status)
(platform, status)
(account_id, status)
(scheduled_at)
(external_publication_id)
(idempotency_key)
```

RLS/project isolation MUST follow `DATABASE_SCHEMA_SPECIFICATION.md`.

Do not introduce a competing schema without first inspecting existing migrations and database code.

---

## 29. Android Boundary

Android responsibilities:

- show publication status;
- create/edit publication intent;
- select platform/account;
- edit metadata;
- select thumbnail/captions;
- schedule;
- trigger publish;
- display errors;
- observe progress/events;
- show verification state;
- display analytics.

Backend responsibilities:

- validation;
- authorization;
- queueing;
- credential access;
- upload;
- scheduling;
- platform API calls;
- retries;
- verification;
- analytics collection.

Android MUST NOT contain platform SDK business workflows as the production source of truth.

---

## 30. Mock Mode

Mock publishing MUST be deterministic and offline.

The mock adapter SHOULD simulate:

```text
validation
upload progress
processing delay
scheduled publication
external ID generation
success
rate limiting
transient failure
permanent failure
verification
analytics availability
```

Mock mode MUST never contact real platforms.

The Golden E2E pipeline SHOULD terminate with:

```text
Final Asset
 → Mock Publishing Job
 → Mock External Publication
 → Verification
 → Mock Analytics Record
```

---

## 31. Testing Strategy

### Unit Tests

Test:

- metadata mapping;
- capability validation;
- schedule normalization;
- idempotency keys;
- retry classification;
- error mapping;
- state transitions;
- analytics normalization.

### Integration Tests

Test:

- upload session handling;
- resumable upload;
- token refresh abstraction;
- webhook processing;
- remote status polling;
- database persistence;
- queue integration.

### Contract Tests

Each adapter MUST validate:

```text
capabilities
validation
upload lifecycle
metadata mapping
thumbnail mapping
caption mapping
schedule behavior
status mapping
error mapping
idempotency behavior
verification
```

### Failure Injection

At minimum simulate:

- timeout after remote acceptance;
- duplicate worker execution;
- HTTP 429;
- HTTP 500;
- invalid token;
- revoked permission;
- malformed media;
- platform rejection;
- upload interruption;
- worker crash;
- webhook duplication;
- out-of-order webhook;
- scheduler restart.

---

## 32. Golden Publishing E2E

The canonical deterministic test is:

```text
Project
 → Episode
 → Story
 → Scenes
 → Shots
 → Mock Generation
 → Assets
 → QC
 → Best Take
 → Timeline
 → Render
 → Final Asset
 → Publication Plan
 → Publishing Job
 → Mock Adapter
 → Upload
 → Metadata
 → Thumbnail
 → Captions
 → Publish
 → Verification
 → Analytics Record
```

The final assertion MUST verify that:

1. the final asset exists and passes integrity checks;
2. the publishing job reached `VERIFIED`;
3. an external publication ID exists;
4. the publication references the correct source hash/snapshot;
5. metadata/thumbnail/caption versions are persisted;
6. analytics can be associated with the verified external publication;
7. no secret was persisted in logs or job payloads.

---

## 33. Implementation Order

Publishing implementation MUST proceed in this order:

### Phase P0 — Contracts

- domain models;
- publishing states;
- API DTOs;
- error codes;
- adapter interfaces;
- capability model.

### Phase P1 — Persistence

- migrations;
- publishing plans/jobs;
- account references;
- metadata versions;
- events;
- indexes;
- project isolation.

### Phase P2 — Mock Adapter

- deterministic adapter;
- upload simulation;
- status/verification;
- failure injection;
- Golden E2E integration.

### Phase P3 — Scheduler Integration

- queue submission;
- dependencies;
- retries;
- rate limits;
- scheduling;
- leases/recovery.

### Phase P4 — First Real Platform Adapter

Implement one platform end-to-end before adding many adapters.

Required stages:

```text
Auth
 → Preflight
 → Upload
 → Metadata
 → Thumbnail
 → Captions
 → Schedule/Publish
 → Verify
 → Error Mapping
 → Contract Tests
```

### Phase P5 — Analytics

- external publication linkage;
- status sync;
- metrics collection;
- normalized analytics records.

### Phase P6 — Additional Platforms

Only after the adapter contract and first integration are stable.

---

## 34. Definition of Done

Publishing is production-ready only when:

- [ ] domain contracts are implemented;
- [ ] database schema/migrations are implemented and tested;
- [ ] project isolation is enforced;
- [ ] preflight blocks invalid publications;
- [ ] final assets are snapshot-based;
- [ ] idempotency is implemented;
- [ ] queue/scheduler integration is persistent;
- [ ] retries are classified correctly;
- [ ] rate limits are respected;
- [ ] credentials are secret-safe;
- [ ] mock adapter works offline;
- [ ] at least one real adapter passes contract/integration tests;
- [ ] remote verification is implemented;
- [ ] scheduling is timezone-safe;
- [ ] thumbnails/captions are versioned;
- [ ] analytics are linked to external publication IDs;
- [ ] structured observability exists;
- [ ] failure injection tests pass;
- [ ] Golden E2E passes;
- [ ] Android consumes the API rather than bypassing it;
- [ ] no fake production behavior remains;
- [ ] documentation matches implementation.

---

## 35. Relationship to Existing Specifications

This specification depends on and MUST remain compatible with:

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
- `TIMELINE_RENDERING_SPECIFICATION.md`

The publishing subsystem is downstream of rendering and QC and upstream of analytics/learning. It MUST NOT duplicate queue, storage, provenance, authentication, or rendering implementations.

---

## 36. Final Architecture

```text
                         ┌──────────────────────┐
                         │       Android        │
                         │  Publish / Schedule  │
                         └──────────┬───────────┘
                                    │ API
                                    ▼
                         ┌──────────────────────┐
                         │ Publishing Service   │
                         │ Auth + Preflight     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Persistent Queue     │
                         │ Scheduler/Leases     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Publishing Worker    │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 ▼                  ▼                  ▼
          ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
          │ Platform A  │    │ Platform B  │    │ Platform C  │
          │   Adapter   │    │   Adapter   │    │   Adapter   │
          └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
                 │                  │                  │
                 └──────────────────┼──────────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Remote Verification  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Analytics Collector  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Analytics / Learning │
                         └──────────────────────┘
```

---

## 37. Final Principle

The publishing subsystem is not a button that calls a social-media API. It is a durable, auditable distributed workflow:

```text
Intent
 → Validated Snapshot
 → Persistent Job
 → Secure Credential Boundary
 → Platform Adapter
 → Idempotent Upload
 → Metadata/Media Completion
 → Schedule/Publish
 → Remote Verification
 → Analytics
```

Every external side effect MUST be recoverable, observable, idempotent, project-isolated, and represented by persistent state.
