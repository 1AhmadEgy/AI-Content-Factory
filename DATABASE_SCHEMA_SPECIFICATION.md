# AI Content Factory — Database Schema Specification

**Version:** 1.0  
**Status:** Normative database design reference  
**Depends on:** `PROJECT_RULES.md`, `DEVELOPER_IMPLEMENTATION_GUIDE.md`, `CONTRACTS_SPECIFICATION.md`

---

## 1. Purpose

هذه الوثيقة تحول الـDomain Contracts إلى تصميم قاعدة بيانات قابل للتنفيذ، مع الحفاظ على فصل:

```text
API Contract != Database Schema != UI State
```

الهدف هو قاعدة بيانات موثوقة للـproduction، قابلة للـmigration، وآمنة من تسرب بيانات المشاريع، ومناسبة لمحرك Jobs والـAssets والـQC والـRendering.

---

## 2. Database Principles

1. PostgreSQL هو المرجع الأساسي لحالة الـBackend production عندما يستخدم المشروع PostgreSQL.
2. Android لا يكتب مباشرة إلى جداول Backend.
3. كل migration يجب أن تكون versioned وقابلة للتتبع.
4. كل جدول إنتاجي يجب أن يملك primary key.
5. العلاقات المهمة تستخدم foreign keys.
6. الحقول المستخدمة في البحث/الفلترة/authorization لا تختبئ داخل JSON فقط.
7. JSONB يستخدم للبيانات المرنة أو provider-specific metadata، وليس لإلغاء النموذج العلائقي.
8. جميع timestamps تخزن UTC.
9. لا تحفظ secrets في قاعدة البيانات إلا إذا كانت هناك آلية secrets management مناسبة ومقصودة؛ الافتراضي هو عدم تخزينها.
10. RLS/authorization يجب أن تمنع الوصول عبر project boundaries.
11. لا حذف cascade عشوائي لبيانات الإنتاج.
12. يجب دعم soft-delete حيث يكون الحذف النهائي خطرًا على provenance أو auditability.

---

## 3. Naming Convention

استخدم snake_case في PostgreSQL:

```text
project_id
created_at
updated_at
max_attempts
```

الجداول بصيغة الجمع:

```text
projects
series
episodes
characters
assets
jobs
```

---

## 4. Common Columns

الجداول الأساسية تستخدم عند الحاجة:

```text
id             UUID/ULID primary key
created_at     timestamptz not null
updated_at     timestamptz not null
```

الجداول التي تحتاج soft-delete:

```text
deleted_at     timestamptz null
```

لا تضف أعمدة عامة بلا حاجة؛ كل عمود يجب أن يخدم domain أو persistence concern واضحًا.

---

## 5. Core Entity Tables

### 5.1 projects

```text
id                  PK
name                NOT NULL
slug                nullable/unique where applicable
description         nullable
status              NOT NULL
settings            JSONB NOT NULL DEFAULT '{}'
created_at          NOT NULL
updated_at          NOT NULL
archived_at         nullable
```

Constraint:

```text
status IN (DRAFT, ACTIVE, ARCHIVED)
```

---

### 5.2 series

```text
id                  PK
project_id          FK -> projects.id
name/title          NOT NULL
description         nullable
genre               nullable
language            NOT NULL
memory              JSONB NOT NULL DEFAULT '{}'
created_at          NOT NULL
updated_at          NOT NULL
```

Index:

```text
(project_id, created_at)
```

---

### 5.3 seasons

```text
id                  PK
series_id           FK -> series.id
season_number       NOT NULL
title               nullable
status              NOT NULL
created_at          NOT NULL
updated_at          NOT NULL
```

Unique:

```text
(series_id, season_number)
```

---

### 5.4 episodes

```text
id                  PK
series_id           FK -> series.id
season_id           nullable FK -> seasons.id
season_number       NOT NULL
episode_number       NOT NULL
title               NOT NULL
status              NOT NULL
target_duration_ms   nullable
story_id            nullable FK -> stories.id
created_at          NOT NULL
updated_at          NOT NULL
```

Recommended unique constraint:

```text
(series_id, season_number, episode_number)
```

---

## 6. Story Tables

### 6.1 stories

```text
id                  PK
episode_id           FK -> episodes.id
title               NOT NULL
logline              nullable
genre                nullable
tone                 nullable
language             NOT NULL
premise              nullable
version              NOT NULL
created_at           NOT NULL
updated_at           NOT NULL
```

### 6.2 story_beats

```text
id                  PK
story_id             FK -> stories.id
order_index          NOT NULL
type                 NOT NULL
summary              nullable
objective            nullable
duration_ms          nullable
created_at           NOT NULL
updated_at           NOT NULL
```

Unique:

```text
(story_id, order_index)
```

---

## 7. Character Tables

### 7.1 characters

```text
id                  PK
project_id           FK -> projects.id
name                NOT NULL
role                NOT NULL
description         nullable
personality         JSONB NOT NULL DEFAULT '[]'
appearance          JSONB NOT NULL DEFAULT '{}'
voice_profile       JSONB NOT NULL DEFAULT '{}'
character_bible     JSONB NOT NULL DEFAULT '{}'
created_at          NOT NULL
updated_at          NOT NULL
```

### 7.2 character_assets

```text
id                  PK
character_id        FK -> characters.id
asset_id            FK -> assets.id
purpose             NOT NULL
created_at          NOT NULL
```

Unique recommendation:

```text
(character_id, asset_id, purpose)
```

---

## 8. World Tables

### 8.1 worlds

```text
id                  PK
project_id           FK -> projects.id
name                NOT NULL
description         nullable
style               JSONB NOT NULL DEFAULT '{}'
rules               JSONB NOT NULL DEFAULT '[]'
created_at           NOT NULL
updated_at           NOT NULL
```

### 8.2 locations

```text
id                  PK
world_id             FK -> worlds.id
name                NOT NULL
description         nullable
visual_style        JSONB NOT NULL DEFAULT '{}'
created_at           NOT NULL
updated_at           NOT NULL
```

### 8.3 location_assets

```text
id                  PK
location_id         FK -> locations.id
asset_id            FK -> assets.id
purpose             NOT NULL
created_at          NOT NULL
```

---

## 9. Scene / Shot Tables

### 9.1 scenes

```text
id                  PK
episode_id           FK -> episodes.id
order_index          NOT NULL
location_id         nullable FK -> locations.id
time_of_day         nullable
summary              nullable
target_duration_ms   nullable
continuity_state    JSONB NOT NULL DEFAULT '{}'
created_at           NOT NULL
updated_at           NOT NULL
```

Unique:

```text
(episode_id, order_index)
```

### 9.2 scene_characters

```text
scene_id             FK -> scenes.id
character_id         FK -> characters.id
role_in_scene        nullable
created_at           NOT NULL
PRIMARY KEY(scene_id, character_id)
```

### 9.3 shots

```text
id                  PK
scene_id             FK -> scenes.id
order_index          NOT NULL
shot_type            NOT NULL
camera               JSONB NOT NULL DEFAULT '{}'
composition         JSONB NOT NULL DEFAULT '{}'
action               nullable
prompt               nullable
negative_prompt      nullable
duration_ms          nullable
generation_requirements JSONB NOT NULL DEFAULT '{}'
status               NOT NULL
created_at           NOT NULL
updated_at           NOT NULL
```

Unique:

```text
(scene_id, order_index)
```

### 9.4 shot_characters

```text
shot_id              FK -> shots.id
character_id         FK -> characters.id
created_at           NOT NULL
PRIMARY KEY(shot_id, character_id)
```

### 9.5 shot_reference_assets

```text
shot_id              FK -> shots.id
asset_id             FK -> assets.id
purpose              nullable
created_at           NOT NULL
PRIMARY KEY(shot_id, asset_id)
```

---

## 10. Dialogue / Voice Tables

### 10.1 voices

```text
id                  PK
name                NOT NULL
language            NOT NULL
locale              nullable
gender              nullable
style               nullable
provider             nullable
model               nullable
settings            JSONB NOT NULL DEFAULT '{}'
created_at          NOT NULL
updated_at          NOT NULL
```

### 10.2 dialogues

```text
id                  PK
scene_id             FK -> scenes.id
character_id         nullable FK -> characters.id
voice_id             nullable FK -> voices.id
order_index          NOT NULL
text                NOT NULL
language            NOT NULL
emotion              nullable
delivery             nullable
duration_ms          nullable
created_at           NOT NULL
updated_at           NOT NULL
```

Unique:

```text
(scene_id, order_index)
```

---

## 11. Asset Tables

### 11.1 assets

```text
id                  PK
project_id           FK -> projects.id
type                NOT NULL
path                NOT NULL
mime                nullable
size_bytes          nullable
sha256              nullable
metadata            JSONB NOT NULL DEFAULT '{}'
provider            nullable
model               nullable
prompt              nullable
negative_prompt      nullable
seed                nullable
job_id              nullable FK -> jobs.id
created_at          NOT NULL
updated_at          NOT NULL
```

### Asset rules

- `sha256` should be unique where content-addressing is intended.
- `path` must not be assumed to be publicly accessible.
- Asset ownership must be checked through `project_id`.
- Asset provenance must remain after downstream processing.

### 11.2 asset_sources

Use when source relationships become more complex than a simple list:

```text
asset_id             FK -> assets.id
source_asset_id      FK -> assets.id
relationship_type    NOT NULL
created_at           NOT NULL
PRIMARY KEY(asset_id, source_asset_id, relationship_type)
```

Examples:

```text
REFERENCE
DERIVED_FROM
UPSCALED_FROM
INTERPOLATED_FROM
LIPSYNC_SOURCE
AUDIO_SOURCE
```

---

## 12. Job Engine Tables

### 12.1 jobs

```text
id                  PK
parent_job_id       nullable FK -> jobs.id
project_id          FK -> projects.id
type                NOT NULL
target_type         NOT NULL
target_id           NOT NULL
priority            NOT NULL DEFAULT 50
status              NOT NULL
progress            NOT NULL DEFAULT 0
attempt             NOT NULL DEFAULT 0
max_attempts        NOT NULL DEFAULT 3
provider            nullable
model               nullable
input               JSONB NOT NULL DEFAULT '{}'
output              JSONB nullable
error_code          nullable
error_message       nullable
created_at          NOT NULL
started_at          nullable
completed_at        nullable
updated_at          NOT NULL
```

Indexes:

```text
(project_id, status, priority, created_at)
(status, priority, created_at)
(target_type, target_id)
(parent_job_id)
```

### 12.2 job_dependencies

```text
job_id              FK -> jobs.id
depends_on_job_id   FK -> jobs.id
created_at          NOT NULL
PRIMARY KEY(job_id, depends_on_job_id)
```

Constraint:

A job cannot directly depend on itself.

Application-level validation should also prevent dependency cycles.

### 12.3 provider_runs

```text
id                  PK
job_id              FK -> jobs.id
provider            NOT NULL
model               nullable
request_metadata    JSONB NOT NULL DEFAULT '{}'
response_metadata   JSONB NOT NULL DEFAULT '{}'
status              NOT NULL
started_at          NOT NULL
completed_at        nullable
duration_ms         nullable
error_code          nullable
created_at          NOT NULL
```

**Security:** never persist API keys, bearer tokens, cookies, passwords, or private credentials in request/response metadata.

### 12.4 job_events

Append-only operational history:

```text
id                  PK
job_id              FK -> jobs.id
event_type          NOT NULL
from_status         nullable
to_status            nullable
message             nullable
metadata            JSONB NOT NULL DEFAULT '{}'
created_at          NOT NULL
```

Use for audit/debugging instead of overwriting history.

---

## 13. QC Tables

### 13.1 qc_results

```text
id                  PK
asset_id            FK -> assets.id
job_id              nullable FK -> jobs.id
status              NOT NULL
score               nullable
summary             nullable
created_at          NOT NULL
```

### 13.2 qc_checks

```text
id                  PK
qc_result_id        FK -> qc_results.id
type                NOT NULL
status              NOT NULL
score               nullable
message             nullable
metadata            JSONB NOT NULL DEFAULT '{}'
created_at          NOT NULL
```

### 13.3 qc_issues

```text
id                  PK
qc_result_id        FK -> qc_results.id
severity            NOT NULL
code                NOT NULL
message             NOT NULL
metadata            JSONB NOT NULL DEFAULT '{}'
created_at          NOT NULL
```

`BLOCKER` يمنع اعتماد Asset عند وجوده ما لم توجد سياسة domain صريحة تسمح بذلك.

---

## 14. Best Take Selection

عندما توجد عدة outputs للـShot، لا تستبدلها بحذف القديم.

### shot_candidates

```text
id                  PK
shot_id              FK -> shots.id
asset_id             FK -> assets.id
qc_result_id         nullable FK -> qc_results.id
score                nullable
selection_status     NOT NULL
rank                nullable
created_at           NOT NULL
updated_at           NOT NULL
```

Statuses:

```text
CANDIDATE | SELECTED | REJECTED
```

هذا يحافظ على history ويمكّن إعادة الاختيار.

---

## 15. Continuity Tables

### continuity_snapshots

```text
id                  PK
episode_id           FK -> episodes.id
scene_id             nullable FK -> scenes.id
shot_id              nullable FK -> shots.id
state                JSONB NOT NULL
created_at           NOT NULL
```

لا تجعل continuity مجرد بيانات UI؛ يجب أن تكون قابلة للاسترجاع وإعادة البناء.

---

## 16. Timeline Tables

### timelines

```text
id                  PK
episode_id           FK -> episodes.id
version              NOT NULL
width                NOT NULL
height               NOT NULL
fps                  NOT NULL
duration_ms          NOT NULL
created_at           NOT NULL
updated_at           NOT NULL
```

Unique:

```text
(episode_id, version)
```

### timeline_tracks

```text
id                  PK
timeline_id          FK -> timelines.id
type                NOT NULL
order_index          NOT NULL
created_at           NOT NULL
updated_at           NOT NULL
```

### timeline_clips

```text
id                  PK
track_id             FK -> timeline_tracks.id
asset_id             FK -> assets.id
start_ms             NOT NULL
duration_ms          NOT NULL
source_start_ms      NOT NULL
source_duration_ms   NOT NULL
volume               nullable
effects              JSONB NOT NULL DEFAULT '[]'
transition_in       JSONB nullable
transition_out      JSONB nullable
created_at           NOT NULL
updated_at           NOT NULL
```

Index:

```text
(track_id, start_ms)
```

---

## 17. Render Tables

### render_jobs

```text
id                  PK
timeline_id          FK -> timelines.id
project_id           FK -> projects.id
status               NOT NULL
output_asset_id      nullable FK -> assets.id
settings             JSONB NOT NULL DEFAULT '{}'
error_code           nullable
error_message        nullable
created_at           NOT NULL
started_at           nullable
completed_at         nullable
updated_at           NOT NULL
```

Render completion requires:

1. output Asset exists;
2. output is readable;
3. technical validation passes;
4. required QC passes;
5. only then `status = COMPLETED`.

---

## 18. Publishing Tables

### publishing_jobs

```text
id                  PK
project_id           FK -> projects.id
episode_id           nullable FK -> episodes.id
asset_id             FK -> assets.id
target               NOT NULL
status               NOT NULL
metadata             JSONB NOT NULL DEFAULT '{}'
external_id          nullable
error_code           nullable
error_message        nullable
created_at           NOT NULL
started_at           nullable
completed_at         nullable
updated_at           NOT NULL
```

Publishing credentials يجب أن تأتي من secure configuration/secret management، وليس من source code أو regular metadata.

---

## 19. Model Registry Tables

### models

```text
id                  PK
name                NOT NULL
version             NOT NULL
category            NOT NULL
provider            NOT NULL
runtime             nullable
capabilities        JSONB NOT NULL DEFAULT '[]'
hardware_requirements JSONB NOT NULL DEFAULT '{}'
license_status      NOT NULL
quality_score       nullable
speed_score         nullable
enabled             NOT NULL DEFAULT true
created_at          NOT NULL
updated_at          NOT NULL
```

Unique recommendation:

```text
(provider, name, version)
```

### model_capabilities

إذا احتاج النظام إلى querying دقيق للقدرات، يمكن تطبيعها:

```text
model_id            FK -> models.id
capability          NOT NULL
created_at          NOT NULL
PRIMARY KEY(model_id, capability)
```

---

## 20. Resource / Worker Tables

لا يجب أن تكون حالة worker الحساسة هي source of truth في قاعدة البيانات وحدها؛ runtime state قد يكون ephemeral.

### worker_registrations

```text
id                  PK
worker_type         NOT NULL
worker_name         NOT NULL
status              NOT NULL
capabilities        JSONB NOT NULL DEFAULT '[]'
hardware            JSONB NOT NULL DEFAULT '{}'
last_heartbeat_at   nullable
created_at          NOT NULL
updated_at          NOT NULL
```

استخدم heartbeat فقط للمراقبة؛ لا تعتمد عليه وحده لإدارة job ownership.

---

## 21. Audit Tables

### audit_events

```text
id                  PK
project_id           nullable FK -> projects.id
actor_type           NOT NULL
actor_id             nullable
action               NOT NULL
entity_type          NOT NULL
entity_id            NOT NULL
metadata             JSONB NOT NULL DEFAULT '{}'
created_at           NOT NULL
```

الأسرار لا تدخل metadata.

---

## 22. Ownership / Authorization

القاعدة الأساسية:

```text
User/Actor -> Project -> Resource
```

أي query على resource يجب أن يتحقق من المشروع/الملكية قبل الإرجاع أو التعديل.

مثال منطقي:

```text
SELECT shot
FROM shots
JOIN scenes ON scenes.id = shots.scene_id
JOIN episodes ON episodes.id = scenes.episode_id
JOIN series ON series.id = episodes.series_id
WHERE shots.id = :shot_id
  AND series.project_id = :authorized_project_id;
```

لا تعتمد على `projectId` المرسل من العميل دون authorization.

---

## 23. RLS / Multi-Tenant Rules

إذا كان Backend يستخدم Supabase/PostgreSQL مع RLS:

- فعّل RLS على الجداول التي تحتوي بيانات مستخدمين/مشاريع.
- أنشئ سياسات قراءة/إضافة/تعديل/حذف وفق membership/ownership.
- اختبر cross-project access صراحة.
- لا تعتبر وجود RLS وحده دليلًا على صحة authorization؛ اختبره من منظور مستخدم فعلي.

---

## 24. Index Strategy

الفهارس الأساسية المتوقعة:

```text
series(project_id)
episodes(series_id)
stories(episode_id)
story_beats(story_id, order_index)
characters(project_id)
worlds(project_id)
locations(world_id)
scenes(episode_id, order_index)
shots(scene_id, order_index)
dialogues(scene_id, order_index)
assets(project_id, type, created_at)
jobs(project_id, status, priority, created_at)
jobs(target_type, target_id)
job_dependencies(depends_on_job_id)
provider_runs(job_id)
qc_results(asset_id)
shot_candidates(shot_id, selection_status)
timelines(episode_id, version)
timeline_tracks(timeline_id, order_index)
timeline_clips(track_id, start_ms)
render_jobs(project_id, status, created_at)
publishing_jobs(project_id, status, created_at)
audit_events(project_id, created_at)
```

لا تضف indexes عشوائيًا؛ راجع query plans عند الحاجة.

---

## 25. Foreign Key Delete Policy

الافتراضي:

```text
RESTRICT / NO ACTION
```

استخدم `CASCADE` فقط لعلاقات child التي لا معنى لها بدون parent، وبعد التأكد من عدم تدمير provenance أو audit data.

مثال مناسب نسبيًا:

```text
story -> story_beats
scene -> scene_characters
scene -> dialogues
```

لكن لا تحذف Assets أو Job history تلقائيًا لمجرد حذف UI entity.

---

## 26. Concurrency Rules

Jobs هي أكثر منطقة حساسة للتزامن.

يجب منع:

```text
worker A -> RUNNING job_01
worker B -> RUNNING job_01
```

في الوقت نفسه.

التنفيذ يجب أن يستخدم آلية atomic claim/lease مناسبة للـdatabase/queue.

المطلوب:

```text
claim
lease/heartbeat where needed
complete atomically
release on failure
recover stale work
```

لا تعتمد على `SELECT ثم UPDATE` غير الذري كآلية وحيدة.

---

## 27. Job State Constraints

الانتقالات القانونية:

```text
PENDING -> QUEUED
QUEUED -> RUNNING
RUNNING -> COMPLETED
RUNNING -> FAILED
RUNNING -> RETRYING
RETRYING -> QUEUED
PENDING -> CANCELLED
QUEUED -> CANCELLED
RUNNING -> CANCELLED
RUNNING -> PAUSED
PAUSED -> QUEUED
```

أي transition غير قانوني يجب رفضه في domain layer.

`job_events` تحفظ التاريخ.

---

## 28. Idempotency

العمليات القابلة لإعادة الإرسال يجب أن تدعم idempotency حيث يكون ذلك ضروريًا.

خصوصًا:

```text
create job
start generation
register asset
render
publish
```

يمكن استخدام:

```text
idempotency_key
```

مع unique constraint مناسب حسب العملية.

لا تستخدم idempotency key عالميًا لجميع العمليات؛ نطاقه يجب أن يكون محددًا بوضوح.

---

## 29. Transactions

Transaction يجب أن تغطي العمليات التي يجب أن تنجح كوحدة واحدة.

مثال إنشاء Job:

```text
validate target
-> create job
-> create dependencies
-> create event
COMMIT
```

أما عملية AI الثقيلة نفسها فلا يجب أن تبقى داخل DB transaction طويلة.

النمط الصحيح:

```text
short DB transaction
-> claim job
-> external/worker execution
-> short DB transaction for result
```

---

## 30. Migration Rules

كل تغيير schema يجب أن يكون migration مستقلًا ومسمى مثل:

```text
001_initial_schema
002_add_job_events
003_add_qc_tables
004_add_timeline_tables
```

قواعد:

1. لا تعدل migration قديمة مطبقة على بيئة مشتركة.
2. migrations الجديدة يجب أن تكون deterministic.
3. destructive migrations تحتاج خطة ترحيل وbackup.
4. أضف indexes الثقيلة بطريقة مناسبة لبيئة production.
5. بعد كل migration شغل schema validation وtests.

---

## 31. Seed Data

Seed data المسموح:

```text
mock providers
mock models
mock voices
sample project
sample comedy story
```

لا تضع:

```text
real API keys
real user credentials
private production identifiers
```

---

## 32. Mock Database Mode

لـCI والاختبارات:

```text
Project
-> Episode
-> Story
-> Character
-> Scene
-> Shot
-> Dialogue
-> Job
-> Asset
-> QC
-> Timeline
-> Render
```

يجب أن يعمل دون GPU أو Provider خارجي.

---

## 33. Android Database Mapping

Android قد يستخدم Room/local database/cache، لكن:

```text
Local DB != Backend DB
```

Android يحتفظ فقط بما يحتاجه للـoffline/cache/UI state.

لا تفترض أن schema المحلي نسخة مطابقة لقاعدة Backend.

يجب وجود mapping:

```text
API DTO
  -> Domain Model
  -> Local Entity
```

والعكس عند الإرسال.

---

## 34. Data Retention

لا تحذف تلقائيًا:

```text
job history
provider runs
asset provenance
QC results
render history
```

إلا وفق سياسة retention موثقة.

الـtemporary worker files يمكن حذفها بعد التأكد من تسجيل الـAsset النهائي.

---

## 35. Performance Rules

ابدأ بالـcorrectness ثم optimization.

يجب مراقبة:

```text
slow queries
large JSONB rows
N+1 queries
unbounded list endpoints
missing indexes
job queue contention
asset metadata growth
```

لا تخزن binary video/audio/image داخل PostgreSQL كقاعدة عامة؛ استخدم object/file storage، وخزن metadata/reference في DB.

---

## 36. Backup / Recovery

Production database يجب أن يكون لها:

```text
backup policy
restore procedure
migration recovery plan
asset storage recovery plan
```

DB backup وحده لا يكفي إذا كانت Assets خارج DB.

يجب أن تكون هناك خطة لاستعادة:

```text
Database + Asset Storage + Configuration
```

---

## 37. Required Database Tests

### Schema

```text
[ ] migrations apply from empty database
[ ] migrations apply sequentially
[ ] schema constraints validated
[ ] foreign keys validated
[ ] unique constraints validated
```

### Authorization

```text
[ ] project A cannot read project B
[ ] project A cannot modify project B
[ ] project A cannot access project B assets
[ ] job target cannot escape project boundary
```

### Jobs

```text
[ ] legal transitions work
[ ] illegal transitions fail
[ ] duplicate claim is prevented
[ ] retry increments attempt
[ ] cancelled job cannot complete normally
[ ] completion requires valid output
```

### Assets

```text
[ ] provenance is persisted
[ ] hash can be stored/queried
[ ] source relationships work
[ ] deleted UI entity does not silently erase required provenance
```

### Timeline/Render

```text
[ ] clips preserve ordering
[ ] timeline versioning works
[ ] render output references valid Asset
[ ] invalid render cannot become COMPLETED
```

---

## 38. Recommended Initial Migration Scope

أول migration فعلية لا تحاول إنشاء كل النظام دفعة واحدة.

الحد الأدنى:

```text
projects
series
seasons
episodes
stories
story_beats
characters
worlds
locations
scenes
scene_characters
shots
shot_characters
voices
dialogues
assets
jobs
job_dependencies
provider_runs
job_events
qc_results
qc_checks
qc_issues
timelines
timeline_tracks
timeline_clips
render_jobs
```

ثم تضاف:

```text
shot_candidates
continuity_snapshots
models
worker_registrations
publishing_jobs
audit_events
```

وفق مراحل التنفيذ الفعلية.

---

## 39. Definition of Database Done

يعتبر تصميم قاعدة البيانات جاهزًا للتنفيذ عندما:

- كل Domain entity لها persistence strategy.
- كل FK مهم محدد.
- كل unique constraint مهم محدد.
- indexes الأساسية محددة.
- Job lifecycle قابل للتطبيق.
- project isolation قابل للاختبار.
- migration strategy محددة.
- asset provenance محفوظ.
- QC history محفوظ.
- timeline versioning محفوظ.
- لا توجد secrets في schema/seed.
- Mock/CI database path معروف.

---

## 40. Implementation Rule

قبل إنشاء الجداول فعليًا في أي بيئة:

```text
READ CONTRACTS_SPECIFICATION.md
→ MAP ENTITIES
→ REVIEW CURRENT REPOSITORY
→ REVIEW EXISTING DATABASE
→ DESIGN MIGRATION
→ TEST ON NON-PRODUCTION
→ APPLY
→ VERIFY
→ DOCUMENT
```

**ممنوع إنشاء schema جديدة فوق schema موجودة دون فحص قاعدة البيانات الحالية وmigrations الحالية أولًا.**

هذه الوثيقة تصف التصميم المستهدف؛ لا تعني أن كل جدول يجب أن يُنشأ فورًا إذا كان المستودع الحالي لا يحتاجه بعد.