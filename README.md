# 🤖 AI Content Factory

AI Content Factory هو نظام مفتوح المصدر لإدارة خط إنتاج المحتوى من المشروع والقصة وحتى المشاهد واللقطات والأصول وعمليات QC والتجميع النهائي والنشر.

## الحالة الحالية

هذا الفرع (`codex/advanced-repair-wave-1`) هو فرع الإصلاح النشط، وليس `main`.

المشروع يتبع سياسة **Real-Only Runtime**: لا توجد نجاحات وهمية، ولا ملفات Media مصطنعة، ولا Dry-Run Publishing يعلن نجاحًا، ولا Provider وهمي مخفي.

## التشغيل المجاني المحلي

يوجد تشغيل محلي مجاني باستخدام Docker + Ollama + FFmpeg، بدون اشتراك AI مدفوع لمسار النصوص:

```bash
cp .env.example .env
bash scripts/free-local-start.sh
```

أو مباشرة:

```bash
docker compose -f docker-compose.free.yml up -d --build
```

بعد التشغيل:

```text
API:     http://127.0.0.1:8000/api/v1/docs
Health:  http://127.0.0.1:8000/api/v1/health
Ready:   http://127.0.0.1:8000/api/v1/ready
Ollama:  http://127.0.0.1:11434
```

التفاصيل: `docs/FREE_LOCAL_RUN.md`.

### ماذا يعمل محليًا؟

- FastAPI API
- SQLite persistence للتشغيل المحلي
- Ollama كنموذج نصي حقيقي
- Worker + Scheduler
- FFmpeg / FFprobe
- Timeline / Render / QC
- Asset hashing وprovenance
- Android كـControl Center

### ما الذي لا يتم تزويره؟

توليد الصور/الفيديو/الصوت يحتاج **Media Provider حقيقي**. إذا لم يتم تكوينه، يفشل Job صراحة بدل إنشاء صورة أو فيديو وهمي.

يمكن استخدام أي مزود محلي/ذاتي الاستضافة متوافق مع `LocalMediaModelAdapter` من خلال:

```text
AICF_MEDIA_PROVIDER_ENDPOINT
AICF_MEDIA_PROVIDER_MODEL
AICF_MEDIA_PROVIDER_CAPABILITIES
```

وهذا مقصود: المجانية لا تعني اختلاق مخرجات غير حقيقية.

## Architecture

```text
Android Control Center
        │
        ▼
     FastAPI
        │
        ├── Projects / Series / Episodes
        ├── Jobs / Queue / Scheduler
        ├── Workers / Providers
        ├── Assets / Provenance
        ├── QC / Best Take
        ├── Timeline
        ├── FFmpeg / FFprobe
        └── Publishing adapters
```

## Android

- Kotlin
- Jetpack Compose
- Room
- Retrofit
- OkHttp
- Coroutines
- Material 3
- JDK 17
- Android SDK 36

التطبيق لا ينفذ FFmpeg أو AI محليًا؛ دوره Control Center للـBackend.

## Backend

الـBackend يستخدم FastAPI، ويحتوي على:

- API v1
- Jobs وOrchestrator
- Persistent queue
- Scheduler
- Workers
- Provider registry
- Asset storage
- Provenance
- QC
- Best Take
- Timeline
- FFmpeg rendering
- Repurposing
- Publishing abstraction

## Real-only guarantees

نجاح العملية لا يعتمد على انتهاء Timer أو وجود ملف فارغ. يجب أن يكون الناتج الحقيقي موجودًا ومخزنًا وقابلًا للتحقق، وتطبق بوابات QC المناسبة.

Publishing لا يعتبر ناجحًا إلا عندما يعيد النظام الخارجي معرفًا خارجيًا حقيقيًا.

## Production

**لا يعتبر هذا الفرع Production Ready بعد.**

الإنتاج يتطلب تنفيذ PostgreSQL runtime وauthorization متعدد المشاريع وidempotency واختبارات distributed recovery قبل السماح بتشغيل `AICF_ENV=production`. التطبيق يفشل مغلقًا إذا حاولت تشغيل Production قبل استكمال هذه المتطلبات.

## الاختبارات

Backend:

```bash
cd backend
python -m pytest
```

Android:

```bash
./gradlew test
./gradlew :app:assembleDebug
```

إذا كانت البيئة لا تستطيع الوصول إلى الإنترنت أو تنزيل dependencies، يجب اعتبار الاختبار **environment-blocked** وليس ناجحًا.

## APK

يتم بناء APK عبر GitHub Actions عند التحديثات المعتمدة. لا يعتبر APK الناتج من CI مفتاح توقيع Play Store إنتاجيًا؛ توقيع التوزيع الرسمي يجب أن يكون منفصلًا.

## Security

لا تضع في Git:

- API keys
- passwords
- production tokens
- signing keys
- provider credentials

استخدم متغيرات البيئة وGitHub Secrets عند الحاجة.

## الوثائق المهمة

- `REAL_ONLY_RUNTIME_POLICY.md`
- `ADVANCED_REPAIR_PLAN.md`
- `CONTRACT_MIGRATION_GATE.md`
- `DATABASE_SCHEMA_SPECIFICATION.md`
- `API_SPECIFICATION.md`
- `CONTRACTS_SPECIFICATION.md`
- `docs/FREE_LOCAL_RUN.md`

## Repository

GitHub: https://github.com/1AhmadEgy/AI-Content-Factory
