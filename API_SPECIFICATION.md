# AI Content Factory — API Specification

**Version:** 1.0  
**Status:** Normative API contract  
**Base path:** `/api/v1`

## 1. Purpose

هذا الملف هو العقد التنفيذي بين Android وأي Client وبين Backend. لا تعتمد الواجهة على تفاصيل قاعدة البيانات أو Provider.

القواعد الأساسية:

- JSON UTF-8.
- IDs opaque strings.
- Timestamps ISO-8601 UTC.
- كل response يجب أن يكون deterministic في البنية.
- منطق التطبيق يعتمد على `error.code` وليس نص `message`.
- جميع العمليات الحساسة تتحقق من authorization وproject ownership.
- العمليات القابلة لإعادة المحاولة تدعم Idempotency.

---

## 2. Headers

### Request

```text
Authorization: Bearer <token>
Content-Type: application/json
Accept: application/json
X-Request-Id: <client-generated-id>
Idempotency-Key: <unique-key>
```

`Idempotency-Key` مطلوب للعمليات التي تنشئ Job أو Resource أو Render/Publish operation عندما تكون قابلة للتكرار.

### Response

```text
Content-Type: application/json
X-Request-Id: <request-id>
```

---

## 3. Standard Response

### Single resource

```json
{
  "data": {},
  "requestId": "req_01"
}
```

### Collection

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "pageSize": 50,
    "total": 100,
    "hasNext": true
  },
  "requestId": "req_01"
}
```

---

## 4. Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {},
    "requestId": "req_01"
  }
}
```

### HTTP mapping

```text
400 VALIDATION_ERROR
401 UNAUTHORIZED
403 FORBIDDEN
404 NOT_FOUND
409 CONFLICT
409 IDEMPOTENCY_CONFLICT
422 DOMAIN_RULE_VIOLATION
429 RATE_LIMITED
500 INTERNAL_ERROR
502 PROVIDER_ERROR
503 RESOURCE_UNAVAILABLE
504 TIMEOUT
```

---

## 5. Projects API

```text
GET    /projects
POST   /projects
GET    /projects/{projectId}
PATCH  /projects/{projectId}
DELETE /projects/{projectId}
```

### Create

```json
{
  "name": "AI Comedy Factory",
  "description": "...",
  "settings": {}
}
```

### Update

PATCH يسمح فقط بالحقول المسموح بها.

---

## 6. Series API

```text
GET   /series?projectId={id}
POST  /series
GET   /series/{seriesId}
PATCH /series/{seriesId}
```

Create:

```json
{
  "projectId": "project_01",
  "title": "AI Comedy",
  "description": "...",
  "genre": "COMEDY",
  "language": "ar"
}
```

---

## 7. Episodes API

```text
GET   /episodes?seriesId={id}
POST  /episodes
GET   /episodes/{episodeId}
PATCH /episodes/{episodeId}
```

Create:

```json
{
  "seriesId": "series_01",
  "seasonNumber": 1,
  "episodeNumber": 1,
  "title": "الذكاء الاصطناعي الغبي",
  "targetDurationMs": 60000
}
```

---

## 8. Story API

```text
GET   /stories/{storyId}
POST  /episodes/{episodeId}/story
PATCH /stories/{storyId}
POST  /stories/{storyId}/generate
```

Generate response يجب أن يعيد Job وليس أن ينتظر اكتمال LLM:

```json
{
  "data": {
    "jobId": "job_story_01",
    "status": "QUEUED"
  }
}
```

---

## 9. Characters API

```text
GET   /characters?projectId={id}
POST  /characters
GET   /characters/{characterId}
PATCH /characters/{characterId}
DELETE /characters/{characterId}
POST  /characters/{characterId}/generate
```

---

## 10. Worlds / Locations API

```text
GET   /worlds?projectId={id}
POST  /worlds
GET   /worlds/{worldId}
PATCH /worlds/{worldId}

GET   /locations?worldId={id}
POST  /locations
GET   /locations/{locationId}
PATCH /locations/{locationId}
```

---

## 11. Scenes API

```text
GET   /scenes?episodeId={id}
POST  /scenes
GET   /scenes/{sceneId}
PATCH /scenes/{sceneId}
DELETE /scenes/{sceneId}
POST  /scenes/{sceneId}/generate
```

---

## 12. Shots API

```text
GET   /shots?sceneId={id}
POST  /shots
GET   /shots/{shotId}
PATCH /shots/{shotId}
DELETE /shots/{shotId}
POST  /shots/{shotId}/generate
POST  /shots/{shotId}/regenerate
```

Generate/regenerate يعيد Job reference.

---

## 13. Dialogue / Voice API

```text
GET   /dialogues?sceneId={id}
POST  /dialogues
PATCH /dialogues/{dialogueId}
DELETE /dialogues/{dialogueId}

GET   /voices?projectId={id}
POST  /voices
PATCH /voices/{voiceId}
```

TTS:

```text
POST /dialogues/{dialogueId}/synthesize
```

Response:

```json
{
  "data": {
    "jobId": "job_tts_01",
    "status": "QUEUED"
  }
}
```

---

## 14. Jobs API

### List

```text
GET /jobs?projectId={id}&status=RUNNING&type=VIDEO_GENERATION&page=1&pageSize=50
```

### Get

```text
GET /jobs/{jobId}
```

### Create

```text
POST /jobs
```

Body:

```json
{
  "type": "VIDEO_GENERATION",
  "targetType": "SHOT",
  "targetId": "shot_01",
  "priority": 50,
  "input": {
    "schemaVersion": 1,
    "parameters": {},
    "referenceAssetIds": [],
    "constraints": {},
    "seed": 12345
  }
}
```

### Actions

```text
POST /jobs/{jobId}/cancel
POST /jobs/{jobId}/retry
POST /jobs/{jobId}/pause
POST /jobs/{jobId}/resume
```

لا يسمح Backend بإجراء transition غير صالح.

---

## 15. Job Status API

`GET /jobs/{jobId}` يجب أن يعيد على الأقل:

```json
{
  "data": {
    "id": "job_01",
    "type": "VIDEO_GENERATION",
    "targetType": "SHOT",
    "targetId": "shot_01",
    "status": "RUNNING",
    "progress": 42,
    "attempt": 1,
    "maxAttempts": 3,
    "provider": "local",
    "model": "model_01",
    "output": null,
    "error": null,
    "createdAt": "2026-09-09T10:30:00Z",
    "startedAt": "2026-09-09T10:31:00Z",
    "completedAt": null,
    "updatedAt": "2026-09-09T10:31:20Z"
  }
}
```

---

## 16. Job Events

Backend يجب أن يوفر event stream عند توفره:

```text
GET /jobs/{jobId}/events
```

Preferred transport:

```text
SSE
```

ويمكن توفير WebSocket لاحقًا عند الحاجة.

Event:

```json
{
  "event": "JOB_PROGRESS",
  "jobId": "job_01",
  "status": "RUNNING",
  "progress": 42,
  "timestamp": "2026-09-09T10:31:20Z"
}
```

الأحداث الأساسية:

```text
JOB_QUEUED
JOB_STARTED
JOB_PROGRESS
JOB_RETRYING
JOB_PAUSED
JOB_COMPLETED
JOB_FAILED
JOB_CANCELLED
ASSET_CREATED
QC_UPDATED
```

Client يجب أن يتحمل duplicate/out-of-order events باستخدام `jobId + timestamp/version` دون فساد الحالة.

---

## 17. Assets API

```text
GET /assets?projectId={id}&type=VIDEO&page=1&pageSize=50
GET /assets/{assetId}
GET /assets/{assetId}/download
GET /assets/{assetId}/metadata
```

Download endpoint يعيد redirect/signed URL عند استخدام object storage؛ لا تعرض storage credentials.

---

## 18. QC API

```text
GET  /qc/{qcId}
GET  /assets/{assetId}/qc
POST /assets/{assetId}/qc
POST /qc/{qcId}/approve
POST /qc/{qcId}/reject
```

Approve ممنوع إذا كان هناك `BLOCKER` غير معالج.

---

## 19. Best Take API

```text
GET  /shots/{shotId}/takes
POST /shots/{shotId}/select-take
```

Body:

```json
{
  "assetId": "asset_01",
  "reason": "highest_qc_score"
}
```

يجب التحقق أن Asset ينتمي إلى Shot وأن QC المطلوب ناجح.

---

## 20. Timeline API

```text
GET   /timelines/{timelineId}
POST  /timelines
PATCH /timelines/{timelineId}
POST  /episodes/{episodeId}/timeline/build
POST  /timelines/{timelineId}/validate
```

Build timeline يعيد Job إذا احتاج معالجة طويلة.

---

## 21. Render API

```text
POST /render
GET  /render/{renderJobId}
POST /render/{renderJobId}/cancel
```

Request:

```json
{
  "timelineId": "timeline_01",
  "output": {
    "container": "mp4",
    "videoCodec": "h264",
    "audioCodec": "aac",
    "width": 1080,
    "height": 1920,
    "fps": 30
  },
  "subtitles": {
    "enabled": true,
    "burnIn": true
  }
}
```

الاستجابة:

```json
{
  "data": {
    "jobId": "render_job_01",
    "status": "QUEUED"
  }
}
```

---

## 22. Publishing API

```text
GET  /publish/providers
POST /publish
GET  /publish/{publishJobId}
POST /publish/{publishJobId}/cancel
```

Publishing لا يبدأ إلا بعد validation للـFinal Asset.

---

## 23. Model Registry API

```text
GET  /models
GET  /models/{modelId}
POST /models/{modelId}/enable
POST /models/{modelId}/disable
POST /models/select
```

لا يعرض endpoint أسرار provider.

---

## 24. Health / Readiness

```text
GET /health
GET /ready
GET /capabilities
```

`/health` يدل أن الخدمة process حي.  
`/ready` يدل أن dependencies الأساسية جاهزة.

مثال:

```json
{
  "status": "READY",
  "version": "1.0.0",
  "capabilities": {
    "story": true,
    "image": true,
    "video": false,
    "tts": true,
    "render": true
  }
}
```

---

## 25. Authentication

الـAPI يجب أن يعمل بمبدأ authenticated-by-default.

كل request محمي يحتاج:

```text
Authorization: Bearer <access-token>
```

لا تسمح endpoints الإنتاج الحساسة بـanonymous access.

Public health endpoint يمكن استثناؤه إذا كان deployment يتطلب ذلك.

---

## 26. Authorization

التحقق يكون على مستوى:

```text
user
project
resource
operation
```

مثال:

```text
User A -> Project A -> Shot A = allowed
User A -> Project B -> Shot B = forbidden
```

لا تعتمد على `projectId` المرسل من العميل وحده.

---

## 27. Idempotency

للعمليات الإنشائية/التنفيذية:

```text
POST /jobs
POST /render
POST /publish
POST /.../generate
```

إذا تكرر نفس `Idempotency-Key` بنفس request fingerprint، يعاد نفس النتيجة المنطقية بدل إنشاء Job ثانٍ.

إذا اختلف body مع نفس key:

```text
409 IDEMPOTENCY_CONFLICT
```

---

## 28. Pagination / Filtering / Sorting

Parameters:

```text
page
pageSize
sort
order
status
type
projectId
createdAfter
createdBefore
```

حد أقصى افتراضي لـ`pageSize` لمنع الاستهلاك المفرط.

---

## 29. Validation

Validation يجب أن يحدث قبل إنشاء Job.

أمثلة:

```text
missing projectId -> VALIDATION_ERROR
unknown targetId -> NOT_FOUND
invalid job transition -> DOMAIN_RULE_VIOLATION
blocked model -> MODEL_LICENSE_BLOCKED
missing dependency -> DOMAIN_RULE_VIOLATION
```

---

## 30. Long-running Operations

أي عملية يحتمل أن تستغرق أكثر من request timeout لا تنتظر completion.

النمط:

```text
POST operation
    ↓
202 Accepted
    ↓
jobId
    ↓
GET job / SSE events
    ↓
COMPLETED / FAILED
```

لا تستخدم synchronous HTTP request كبديل عن Queue.

---

## 31. API Versioning

الإصدار الحالي:

```text
/v1
```

Breaking changes تنتقل إلى `/v2`.

Non-breaking additions يمكن أن تبقى في نفس الإصدار.

---

## 32. Security Rules

ممنوع إرسال:

```text
API keys
provider secrets
passwords
refresh tokens
internal credentials
```

إلى Android أو logs أو public API responses.

لا تكشف stack traces في production.

---

## 33. Rate Limiting

طبّق limits منفصلة حسب:

```text
read
write
job creation
generation
render
publish
```

الرد عند التجاوز:

```text
429 RATE_LIMITED
Retry-After: <seconds>
```

---

## 34. Android Integration Pattern

التدفق الإلزامي:

```text
UI
 ↓
ViewModel
 ↓
UseCase
 ↓
Repository
 ↓
API Client
 ↓
Backend
```

Android لا يستدعي provider SDK مباشرة.

Android لا يفترض أن `POST /generate` يعيد Asset نهائيًا؛ غالبًا يعيد Job.

---

## 35. Contract Testing

يجب إنشاء fixtures مشتركة للـDTOs واختبار:

```text
Request serialization
Response deserialization
Error parsing
Enum compatibility
Unknown-field tolerance
Required-field validation
Idempotency
Job lifecycle
```

يجب تشغيل Contract Tests في CI قبل الدمج.

---

## 36. Golden API Flow

```text
POST /projects
POST /series
POST /episodes
POST /episodes/{id}/story
GET  /jobs/{id}
POST /characters
POST /worlds
POST /scenes
POST /shots
POST /dialogues
POST /dialogues/{id}/synthesize
POST /shots/{id}/generate
GET  /jobs/{id}
GET  /assets/{id}
GET  /assets/{id}/qc
POST /shots/{id}/select-take
POST /episodes/{id}/timeline/build
POST /render
GET  /render/{id}
POST /publish
```

يجب أن ينجح هذا المسار في Mock mode دون GPU أو Provider مدفوع.

---

## 37. API Definition of Done

لا يعتبر endpoint مكتملًا إلا إذا كان لديه:

- request schema
- response schema
- validation
- authorization
- error mapping
- idempotency عند الحاجة
- persistence
- tests
- logging آمن
- documentation
- migration إن لزم
- integration مع Golden E2E عند ارتباطه بالـpipeline

---

## 38. Non-Negotiable API Rules

1. لا fake success.
2. لا endpoint يعيد `200 COMPLETED` قبل اكتمال العملية فعليًا.
3. لا secrets في responses/logs.
4. لا authorization يعتمد على client-supplied projectId فقط.
5. لا long-running AI operation تنتظر داخل HTTP request.
6. لا breaking change صامت.
7. لا تعتمد Android على نصوص الأخطاء.
8. لا إنشاء Job مكرر بسبب retry network دون Idempotency.
9. لا Asset download يكشف storage credentials.
10. كل contract change يجب أن يملك tests.

---

## 39. Developer Execution Rule

عند إضافة endpoint جديد:

```text
DEFINE CONTRACT
→ DEFINE AUTH
→ DEFINE VALIDATION
→ DEFINE ERRORS
→ DEFINE PERSISTENCE
→ IMPLEMENT
→ TEST
→ RUN GOLDEN FLOW
→ DOCUMENT
```

**هذا الملف مع `CONTRACTS_SPECIFICATION.md` و`DATABASE_SCHEMA_SPECIFICATION.md` يشكلان العقد الرسمي للاتصال بين مكونات النظام.**