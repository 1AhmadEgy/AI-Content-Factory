# AI Content Factory — Contracts Specification

**Version:** 1.0  
**Status:** Normative implementation contract  
**Audience:** Android, Backend, Workers, AI Providers, QC, Rendering, QA, Codex

> هذه الوثيقة تحدد العقود المشتركة بين طبقات المشروع. أي تنفيذ يخالفها يجب اعتباره تغييرًا معماريًا ويحتاج إلى توثيق واختبارات قبل الدمج.

---

## 1. الهدف

الهدف هو أن تتعامل Android وBackend وWorkers وProviders وQC وRenderer مع نفس المفاهيم والـIDs والحالات دون اعتماد طبقة على تفاصيل طبقة أخرى.

المبادئ:

1. `ID` ثابت وغير قابل لإعادة الاستخدام.
2. كل كيان قابل للتتبع عبر `projectId` عند الحاجة.
3. كل Job له مدخلات ومخرجات وحالة واضحة.
4. لا تعتبر العملية ناجحة بمجرد انتهاء العملية؛ النجاح يتطلب Output صالحًا وQC المطلوب.
5. كل Asset مولد يجب أن يحتفظ بـ provenance.
6. العقود مستقلة عن Android وCompose وRoom وRetrofit وFFmpeg وأي Provider.
7. أي JSON/API contract يجب أن يكون قابلًا للإصدار Versioning.

---

## 2. قواعد عامة للـIDs والتواريخ

### IDs

استخدم UUID/ULID أو معرفًا مكافئًا فريدًا. لا تستخدم أسماء المستخدم أو timestamps وحدها كمعرف.

### Timestamps

كل timestamp في العقود الخارجية يكون ISO-8601 UTC.

أمثلة:

```text
2026-09-09T10:30:00Z
```

### Nullability

- الحقول المطلوبة لا تقبل `null`.
- الحقول الاختيارية يجب أن تكون موثقة صراحة.
- لا تستخدم `null` بدل حالة domain واضحة.

### Pagination

```json
{
  "items": [],
  "page": 1,
  "pageSize": 50,
  "total": 0,
  "hasNext": false
}
```

---

## 3. Project Contract

```json
{
  "id": "project_01",
  "name": "My AI Factory",
  "description": "...",
  "status": "ACTIVE",
  "settings": {},
  "createdAt": "2026-09-09T10:30:00Z",
  "updatedAt": "2026-09-09T10:30:00Z"
}
```

### Status

```text
DRAFT | ACTIVE | ARCHIVED
```

---

## 4. Series / Season / Episode

### Series

```json
{
  "id": "series_01",
  "projectId": "project_01",
  "title": "AI Comedy",
  "description": "...",
  "genre": "COMEDY",
  "language": "ar",
  "memory": {},
  "createdAt": "2026-09-09T10:30:00Z",
  "updatedAt": "2026-09-09T10:30:00Z"
}
```

### Episode

```json
{
  "id": "episode_01",
  "seriesId": "series_01",
  "seasonNumber": 1,
  "episodeNumber": 1,
  "title": "الذكاء الاصطناعي الغبي",
  "status": "DRAFT",
  "targetDurationMs": 60000,
  "storyId": "story_01",
  "createdAt": "2026-09-09T10:30:00Z",
  "updatedAt": "2026-09-09T10:30:00Z"
}
```

---

## 5. Story Contract

```json
{
  "id": "story_01",
  "episodeId": "episode_01",
  "title": "الذكاء الاصطناعي الغبي",
  "logline": "...",
  "genre": "COMEDY",
  "tone": "FAST_COMEDY",
  "language": "ar",
  "premise": "...",
  "beats": [],
  "continuityRules": [],
  "version": 1,
  "createdAt": "2026-09-09T10:30:00Z",
  "updatedAt": "2026-09-09T10:30:00Z"
}
```

### Story Beat

```json
{
  "id": "beat_01",
  "order": 1,
  "type": "SETUP",
  "summary": "...",
  "objective": "...",
  "durationMs": 5000
}
```

Allowed beat types:

```text
HOOK | SETUP | ESCALATION | MISDIRECTION | PAYOFF | TAG | TRANSITION
```

---

## 6. Character Contract

```json
{
  "id": "character_01",
  "projectId": "project_01",
  "name": "محمود",
  "role": "PROTAGONIST",
  "description": "...",
  "personality": [],
  "appearance": {},
  "voiceProfile": {},
  "characterBible": {},
  "referenceAssetIds": [],
  "createdAt": "2026-09-09T10:30:00Z",
  "updatedAt": "2026-09-09T10:30:00Z"
}
```

### Role

```text
PROTAGONIST | ANTAGONIST | SUPPORTING | NARRATOR | EXTRA
```

### Character Bible minimum

```text
identity
appearance
ageRange
bodyType
hair
face
clothing
colors
personality
speechStyle
behaviorRules
visualInvariants
negativeTraits
```

`visualInvariants` هي السمات التي يجب الحفاظ عليها بين اللقطات.

---

## 7. World / Location Contract

```json
{
  "id": "world_01",
  "projectId": "project_01",
  "name": "عالم المصنع",
  "description": "...",
  "style": {},
  "rules": [],
  "locations": []
}
```

### Location

```json
{
  "id": "location_01",
  "worldId": "world_01",
  "name": "غرفة المكتب",
  "description": "...",
  "visualStyle": {},
  "referenceAssetIds": [],
  "continuityRules": []
}
```

---

## 8. Scene Contract

```json
{
  "id": "scene_01",
  "episodeId": "episode_01",
  "order": 1,
  "locationId": "location_01",
  "timeOfDay": "DAY",
  "summary": "...",
  "characterIds": ["character_01"],
  "dialogueIds": [],
  "shotIds": [],
  "continuityState": {},
  "targetDurationMs": 12000
}
```

---

## 9. Shot Contract

```json
{
  "id": "shot_01",
  "sceneId": "scene_01",
  "order": 1,
  "shotType": "MEDIUM",
  "camera": {},
  "composition": {},
  "action": "...",
  "characterIds": ["character_01"],
  "prompt": "...",
  "negativePrompt": "...",
  "referenceAssetIds": [],
  "durationMs": 4000,
  "generationRequirements": {},
  "status": "DRAFT"
}
```

### Shot types

```text
ECU | CLOSE_UP | MEDIUM | MEDIUM_WIDE | WIDE | EXTREME_WIDE | OVER_SHOULDER | POV | INSERT
```

### Camera minimum fields

```text
movement
lens
angle
framing
speed
stabilization
```

---

## 10. Dialogue Contract

```json
{
  "id": "dialogue_01",
  "sceneId": "scene_01",
  "characterId": "character_01",
  "text": "...",
  "language": "ar",
  "emotion": "COMEDIC",
  "delivery": "FAST",
  "voiceId": "voice_01",
  "order": 1,
  "durationMs": 1800
}
```

لا يفترض الـTTS أن يعرف شيئًا عن Scene أو UI؛ يحصل على عقد Dialogue/Voice صالح فقط.

---

## 11. Voice Contract

```json
{
  "id": "voice_01",
  "name": "Arabic Male 01",
  "language": "ar",
  "locale": "ar-LY",
  "gender": "MALE",
  "style": "COMEDIC",
  "provider": "local",
  "model": "...",
  "settings": {}
}
```

---

## 12. Generation Job Contract

هذا أهم عقد في النظام.

```json
{
  "id": "job_01",
  "parentJobId": null,
  "projectId": "project_01",
  "type": "VIDEO_GENERATION",
  "targetType": "SHOT",
  "targetId": "shot_01",
  "priority": 50,
  "status": "PENDING",
  "progress": 0,
  "attempt": 0,
  "maxAttempts": 3,
  "provider": null,
  "model": null,
  "input": {},
  "output": null,
  "errorCode": null,
  "errorMessage": null,
  "createdAt": "2026-09-09T10:30:00Z",
  "startedAt": null,
  "completedAt": null,
  "updatedAt": "2026-09-09T10:30:00Z"
}
```

### Job Types

```text
STORY_GENERATION
CHARACTER_GENERATION
WORLD_GENERATION
SCENE_GENERATION
SHOT_GENERATION
IMAGE_GENERATION
VIDEO_GENERATION
TTS_GENERATION
LIPSYNC_GENERATION
MUSIC_GENERATION
SFX_GENERATION
UPSCALE
INTERPOLATION
QC
TIMELINE_BUILD
RENDER
SUBTITLE_GENERATION
THUMBNAIL_GENERATION
METADATA_GENERATION
PUBLISH
```

### Lifecycle

```text
PENDING
  -> QUEUED
  -> RUNNING
  -> COMPLETED

RUNNING -> RETRYING -> QUEUED
RUNNING -> FAILED
PENDING/QUEUED/RUNNING -> CANCELLED
RUNNING -> PAUSED
PAUSED -> QUEUED
```

لا يجوز الانتقال مباشرة إلى `COMPLETED` بدون validation للـoutput.

---

## 13. Job Input Contract

كل Job يجب أن يحتوي على input قابل لإعادة التنفيذ.

```json
{
  "schemaVersion": 1,
  "parameters": {},
  "referenceAssetIds": [],
  "constraints": {},
  "seed": 12345,
  "deterministic": true
}
```

إذا كان الـprovider لا يدعم `seed`، يبقى الحقل optional لكن يجب تسجيل ما أمكن من معلومات reproducibility.

---

## 14. Job Output Contract

```json
{
  "schemaVersion": 1,
  "assetIds": ["asset_01"],
  "metrics": {},
  "providerRunId": "run_01"
}
```

Output ليس مجرد path؛ يجب أن يشير إلى Asset مسجل.

---

## 15. Provider Run Contract

```json
{
  "id": "run_01",
  "jobId": "job_01",
  "provider": "local",
  "model": "model_v1",
  "request": {},
  "response": {},
  "status": "COMPLETED",
  "startedAt": "2026-09-09T10:30:00Z",
  "completedAt": "2026-09-09T10:31:00Z",
  "durationMs": 60000,
  "errorCode": null
}
```

يجب ألا تسجل الأسرار أو access tokens داخل `request`/`response` أو logs.

---

## 16. Asset Contract

```json
{
  "id": "asset_01",
  "projectId": "project_01",
  "type": "VIDEO",
  "path": "assets/project_01/shot_01/video_01.mp4",
  "mime": "video/mp4",
  "size": 12345678,
  "hash": "sha256:...",
  "metadata": {},
  "provider": "local",
  "model": "model_v1",
  "prompt": "...",
  "sourceAssetIds": [],
  "createdAt": "2026-09-09T10:30:00Z"
}
```

### Asset Types

```text
IMAGE | VIDEO | AUDIO | VOICE | MUSIC | SFX | SUBTITLE | THUMBNAIL | DOCUMENT | MODEL_OUTPUT | OTHER
```

### Provenance minimum

```text
provider
model
prompt
negativePrompt
seed
sourceAssetIds
jobId
createdAt
```

---

## 17. QC Contract

```json
{
  "id": "qc_01",
  "assetId": "asset_01",
  "jobId": "job_01",
  "status": "PASSED",
  "score": 0.91,
  "checks": [],
  "issues": [],
  "createdAt": "2026-09-09T10:35:00Z"
}
```

### QC layers

```text
TECHNICAL
MEDIA
CONTINUITY
SEMANTIC
```

### Check

```json
{
  "type": "VIDEO_READABLE",
  "status": "PASSED",
  "score": 1.0,
  "message": "..."
}
```

### Issue severity

```text
INFO | WARNING | ERROR | BLOCKER
```

`BLOCKER` يمنع اعتماد الـAsset.

---

## 18. Continuity Contract

```json
{
  "characterState": {},
  "locationState": {},
  "propsState": {},
  "wardrobeState": {},
  "timeState": {},
  "cameraState": {}
}
```

كل Scene/Shot يمكن أن يقرأ الحالة السابقة ويكتب state جديدًا بعد نجاح QC.

---

## 19. Timeline Contract

```json
{
  "id": "timeline_01",
  "episodeId": "episode_01",
  "version": 1,
  "durationMs": 60000,
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "tracks": [],
  "createdAt": "2026-09-09T10:40:00Z",
  "updatedAt": "2026-09-09T10:40:00Z"
}
```

### Track

```json
{
  "id": "track_video_01",
  "type": "VIDEO",
  "order": 1,
  "clips": []
}
```

### Clip

```json
{
  "id": "clip_01",
  "assetId": "asset_01",
  "startMs": 0,
  "durationMs": 4000,
  "sourceStartMs": 0,
  "sourceDurationMs": 4000,
  "volume": 1.0,
  "effects": [],
  "transitionIn": null,
  "transitionOut": null
}
```

Track types:

```text
VIDEO | DIALOGUE | VOICE | MUSIC | SFX | SUBTITLE | OVERLAY | EFFECT
```

---

## 20. Render Contract

### Render Job Input

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

Renderer يجب أن يعيد Asset نهائيًا بعد التحقق من قابلية القراءة.

---

## 21. API Contract

Base path:

```text
/api/v1
```

### Resources

```text
GET    /projects
POST   /projects
GET    /projects/{id}
PATCH  /projects/{id}

GET    /series
POST   /series
GET    /series/{id}

GET    /episodes
POST   /episodes
GET    /episodes/{id}

GET    /characters
POST   /characters
PATCH  /characters/{id}

GET    /worlds
POST   /worlds

GET    /scenes
POST   /scenes
PATCH  /scenes/{id}

GET    /shots
POST   /shots
PATCH  /shots/{id}

GET    /jobs
POST   /jobs
GET    /jobs/{id}
POST   /jobs/{id}/cancel
POST   /jobs/{id}/retry

GET    /assets
GET    /assets/{id}

GET    /qc/{id}
POST   /qc/{id}/approve

GET    /timelines/{id}
POST   /timelines

POST   /render
GET    /render/{id}

POST   /publish
GET    /publish/{id}
```

### API errors

```json
{
  "error": {
    "code": "JOB_NOT_FOUND",
    "message": "Job was not found",
    "details": {},
    "requestId": "req_01"
  }
}
```

لا تعتمد Android على نص `message` لاتخاذ قرار منطقي؛ استخدم `code`.

---

## 22. Standard Error Codes

```text
VALIDATION_ERROR
UNAUTHORIZED
FORBIDDEN
NOT_FOUND
CONFLICT
RATE_LIMITED
INTERNAL_ERROR
PROVIDER_UNAVAILABLE
MODEL_UNAVAILABLE
MODEL_LICENSE_BLOCKED
RESOURCE_UNAVAILABLE
GPU_UNAVAILABLE
QUEUE_ERROR
JOB_NOT_FOUND
JOB_NOT_CANCELLABLE
JOB_NOT_RETRYABLE
ASSET_NOT_FOUND
ASSET_CORRUPTED
QC_FAILED
QC_BLOCKED
RENDER_FAILED
PUBLISH_FAILED
TIMEOUT
CANCELLED
```

---

## 23. Retry Policy

Retry تلقائي فقط للأخطاء المؤقتة مثل:

```text
PROVIDER_UNAVAILABLE
RESOURCE_UNAVAILABLE
RATE_LIMITED
TIMEOUT
```

ولا تعيد المحاولة تلقائيًا للأخطاء المنطقية مثل:

```text
VALIDATION_ERROR
MODEL_LICENSE_BLOCKED
ASSET_CORRUPTED
QC_BLOCKED
```

استخدم exponential backoff مع حد أعلى، وسجل كل attempt.

---

## 24. Worker Contract

كل Worker يجب أن يلتزم منطقيًا بالعقد التالي:

```text
initialize()
healthCheck()
execute(job)
cancel(job)
shutdown()
```

`execute(job)` يجب أن:

1. يتحقق من input.
2. يتحقق من الموارد المطلوبة.
3. يسجل Provider Run.
4. ينفذ العملية.
5. يسجل Asset output.
6. ينفذ validation/QC المطلوب.
7. يعيد JobResult صالحًا.

---

## 25. Worker Result Contract

```json
{
  "success": true,
  "assetIds": ["asset_01"],
  "providerRunId": "run_01",
  "metrics": {},
  "warnings": [],
  "error": null
}
```

في حالة الفشل:

```json
{
  "success": false,
  "assetIds": [],
  "providerRunId": "run_01",
  "metrics": {},
  "warnings": [],
  "error": {
    "code": "PROVIDER_UNAVAILABLE",
    "message": "...",
    "retryable": true
  }
}
```

---

## 26. Model Registry Contract

```json
{
  "id": "model_01",
  "name": "Example Model",
  "version": "1.0",
  "category": "VIDEO",
  "provider": "local",
  "runtime": "...",
  "capabilities": [],
  "hardwareRequirements": {},
  "license": "VERIFIED",
  "quality": 0.8,
  "speed": 0.6,
  "enabled": true
}
```

### License status

```text
VERIFIED | UNKNOWN | RESTRICTED | BLOCKED
```

`UNKNOWN` لا تعني أن الاستخدام آمن أو مسموح.

---

## 27. Model Router Contract

الـRouter يختار model/provider بناءً على:

```text
capability
quality target
speed target
hardware
memory
license
availability
cost
user policy
```

يجب أن يعيد سبب الاختيار في metadata قابلة للتدقيق.

---

## 28. Queue Contract

كل queued job يجب أن يحتفظ بـ:

```text
jobId
priority
createdAt
scheduledAt
attempt
dependencies
resourceRequirements
```

### Dependencies

Job لا يبدأ قبل اكتمال dependencies المطلوبة.

مثال:

```text
TTS Job
  depends on
Dialogue + Voice

LipSync Job
  depends on
Video + Voice

Render Job
  depends on
Best Takes + Timeline + QC
```

---

## 29. Android Contract

Android لا يعرف تفاصيل Provider.

Android يتعامل مع:

```text
Project
Episode
Story
Character
Scene
Shot
Job
Asset
QC
Timeline
Render
```

Android يعرض الحالة ويطلب عمليات عبر Repository/API/UseCase.

ممنوع:

```text
Compose -> OpenAI
Compose -> FFmpeg
Compose -> ComfyUI
Compose -> GPU
ViewModel -> Provider SDK
```

---

## 30. Offline / Mock Contract

يجب أن يوجد Mock mode deterministic لا يحتاج إلى الإنترنت أو GPU.

Mock Worker لكل فئة أساسية يجب أن يستطيع إنتاج:

```text
valid fake metadata
small valid media when practical
predictable Job status
predictable Asset
predictable QC
```

الهدف هو تشغيل Golden E2E بالكامل في CI بدون نماذج ثقيلة.

---

## 31. Security Contract

ممنوع تخزين:

```text
API keys
access tokens
refresh tokens
passwords
private credentials
```

داخل:

```text
Git
source code
fixtures
logs
error messages
API responses
Asset metadata
```

إلا إذا كانت قيمة مصطنعة وغير سرية بوضوح.

---

## 32. Project Isolation

كل resource إنتاجي يجب أن يكون قابلًا للربط بالمشروع المناسب، وأي query/update يجب أن يتحقق من ownership/authorization.

لا يجوز قبول `projectId` من العميل ثم تجاهل authorization.

---

## 33. Golden E2E Contract

الاختبار المرجعي:

```text
Create Project
  -> Create Series
  -> Create Episode
  -> Generate Story
  -> Create Characters
  -> Create World
  -> Create Scenes
  -> Create Shots
  -> Create Dialogue
  -> Queue Jobs
  -> Run Mock Workers
  -> Register Assets
  -> Run QC
  -> Select Best Takes
  -> Build Timeline
  -> Render
  -> Validate Final Asset
```

### Acceptance

يعتبر الاختبار ناجحًا إذا:

- كل entity IDs مترابطة صحيـحًا.
- لا توجد Jobs عالقة.
- كل required dependencies مكتملة.
- Assets النهائية موجودة وقابلة للقراءة.
- QC النهائي لا يحتوي BLOCKER.
- Timeline صالح.
- Render output صالح.
- يمكن تتبع Final Video إلى Jobs وAssets وProviders الأصلية.

---

## 34. Contract Versioning

كل contract قابل للتغيير يجب أن يحمل `schemaVersion` عند الحاجة.

قواعد:

1. لا تكسر consumer قائمًا دون migration.
2. التغييرات breaking تحتاج version جديد.
3. التغييرات الإضافية المتوافقة يمكن أن تبقى في نفس version.
4. أي تغيير في enum يجب مراجعة جميع consumers.
5. يجب تحديث fixtures وtests مع العقد.

---

## 35. Database Mapping

لا يشترط أن يكون شكل DB مطابقًا 1:1 للـAPI JSON.

المبدأ:

```text
API Contract != Database Schema != UI State
```

يجب وجود mapping واضح بينها.

لا تستخدم JSON blobs لإخفاء domain data التي تحتاج:

```text
query
filter
sort
authorization
foreign keys
unique constraints
```

---

## 36. Required Tests per Contract

لكل contract رئيسي:

- serialization test
- deserialization test
- validation test
- invalid-input test
- backward-compatibility test عند الحاجة
- API integration test إذا كان API contract
- persistence mapping test إذا كان persisted

للـJob خصوصًا:

- lifecycle transitions
- retryability
- cancellation
- dependency blocking
- duplicate execution protection
- completion validation

---

## 37. Implementation Order

الترتيب الإلزامي المقترح:

### P0

1. IDs/time primitives
2. Project
3. Episode/Series
4. Story
5. Character
6. World/Location
7. Scene
8. Shot
9. Dialogue
10. Asset

### P1

11. GenerationJob
12. Job lifecycle/state machine
13. ProviderRun
14. Queue
15. Worker interface
16. Mock Workers

### P2

17. Model Registry
18. Model Router
19. Real Providers
20. Resource Manager

### P3

21. QC
22. Continuity
23. Best Take selection
24. Timeline
25. Renderer

### P4

26. Publishing
27. Analytics
28. Learning
29. Advanced automation

---

## 38. Non-Negotiable Rules

1. لا fake success.
2. لا `COMPLETED` بدون output صالح.
3. لا provider calls من UI.
4. لا secrets في Git.
5. لا اعتماد production على in-memory state.
6. لا model بدون license status.
7. لا Asset بدون provenance.
8. لا retry عشوائي.
9. لا cross-project data leakage.
10. لا breaking contract change بدون version/migration.
11. لا حذف domain data لإخفاء فشل test.
12. لا إضافة abstraction غير ضرورية قبل فهم الكود الحالي.

---

## 39. Developer Checklist

قبل تنفيذ أي feature:

```text
[ ] تحديد الـdomain entity
[ ] تحديد contract
[ ] تحديد state transitions
[ ] تحديد persistence
[ ] تحديد API
[ ] تحديد errors
[ ] تحديد retry policy
[ ] تحديد tests
[ ] تحديد logging
[ ] تحديد security implications
[ ] تحديد migration إن وجدت
```

بعد التنفيذ:

```text
[ ] Unit tests
[ ] Integration tests
[ ] E2E impact
[ ] Build
[ ] Existing tests still pass
[ ] No secrets
[ ] No dead code
[ ] Documentation updated
[ ] Git diff reviewed
```

---

## 40. المرجع النهائي

عند التعارض بين تنفيذ قديم وهذه الوثيقة، لا يتم تعديل السلوك بصمت.

يجب:

1. تحديد التعارض.
2. تقييم تأثيره.
3. تحديث العقد أو تحديث التنفيذ.
4. إضافة migration إن لزم.
5. إضافة/تحديث tests.
6. توثيق القرار.

**قاعدة التنفيذ:**

```text
READ
→ UNDERSTAND
→ MAP
→ CONTRACT
→ IMPLEMENT
→ TEST
→ BUILD
→ REVIEW
→ DOCUMENT
```

هذه الوثيقة هي العقد المشترك بين Android وBackend وWorkers وProviders وQC وRenderer، إلى أن يصدر إصدار أحدث منها.