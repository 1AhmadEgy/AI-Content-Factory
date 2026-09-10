# AI Content Factory

نظام مفتوح المصدر لبناء خط إنتاج محتوى فيديو بالذكاء الاصطناعي، مع Backend مركزي لإدارة Jobs وAssets وQC وProvenance وتطبيق Android.

## 📱 تحميل APK

### ⬇️ تحميل مباشر — ضغطة واحدة

**[تحميل أحدث APK](https://github.com/1AhmadEgy/AI-Content-Factory/releases/latest/download/AI-Content-Factory.apk)**

إذا لم يوجد إصدار منشور بعد، استخدم تبويب **Actions** لبناء APK، ثم أنشئ Release بالـtag مثل `v0.1.0`.

> الـAPK المنشور حاليًا من خط الإصدار هو Debug APK للتجربة. لا يُعامل كتوقيع إنتاجي نهائي.

## Architecture

- Android / Jetpack Compose
- FastAPI Backend
- SQLite persistence
- Provider-agnostic Worker interface
- Durable Job Queue + leases + retry semantics
- Asset storage by SHA-256
- Provenance attached to persisted Assets
- Mandatory server-side completion gate
- Deterministic QC before `COMPLETED`
- API version: `/api/v1`

## Job lifecycle

```text
PENDING → QUEUED → RUNNING
                    ├─→ COMPLETED   (worker + asset + verification + provenance + QC passed)
                    ├─→ BLOCKED     (completion/QC gate rejected output)
                    ├─→ FAILED      (non-retryable failure or retry budget exhausted)
                    ├─→ RETRYING → QUEUED
                    └─→ CANCELLED
```

Android does **not** invent progress, completion, approval, or successful output. Job state is read from the Backend.

## API

- Swagger: `/api/v1/docs`
- OpenAPI: `/api/v1/openapi.json`
- Health: `/api/v1/health`
- Readiness: `/api/v1/ready`
- Jobs: `/api/v1/jobs`
- Factory: `/api/v1/factory`
- Pipeline: `/api/v1/pipeline`

## Local backend

```bash
cd backend
pip install -e ".[test]"
pytest -q
uvicorn app.main:app --reload --port 8000
```

## Android build

```bash
gradle assembleDebug
gradle testDebugUnitTest
```

The GitHub Actions Android workflow builds and uploads the APK as an artifact. Tagging a release with `v*` builds `AI-Content-Factory.apk` and attaches it to the GitHub Release.

## Current scope

This stabilization stage intentionally does not implement real AI providers, authentication/authorization, PostgreSQL, WebSocket/SSE, dependency DAG, hardware routing, License Guard, or production FFmpeg rendering.

## License

See the repository license and specification documents for the current project terms.
