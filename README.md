# 🤖 AI Content Factory

AI Content Factory هو نظام لإنتاج المحتوى بشكل آلي، يبدأ من الفكرة أو القصة، ثم يحولها إلى مشاريع وحلقات ومشاهد ولقطات وأصول صوتية وبصرية، مع تنفيذ عمليات QC واختيار أفضل Take وتجميع الناتج النهائي.

---

## 📱 تحميل التطبيق

### ⬇️ تحميل APK مباشرة

[![📱 تحميل APK](https://img.shields.io/badge/📱_تحميل_APK-تحميل_مباشر-success?style=for-the-badge)](https://github.com/1AhmadEgy/AI-Content-Factory/releases/latest/download/AI-Content-Factory.apk)

> اضغط على الزر وسيبدأ تحميل أحدث ملف APK مباشرة.

---

## 🚀 آخر إصدار

يتم إنشاء APK تلقائيًا بواسطة GitHub Actions عند تحديث فرع `main`.

اسم الملف:

```text
AI-Content-Factory.apk
```

رابط التحميل المباشر:

https://github.com/1AhmadEgy/AI-Content-Factory/releases/latest/download/AI-Content-Factory.apk

## 🏗️ Architecture

```text
Android App
     │
     │ REST API
     ▼
  FastAPI
     │
     ├── Jobs
     ├── Projects
     ├── Assets
     ├── Pipeline
     ├── Scheduler
     ├── Workers
     └── Publishing
            │
            ▼
       Media Engine
            │
            ▼
       FFmpeg / QC
            │
            ▼
        Final MP4
```

## 📱 Android

التطبيق مبني باستخدام:

- Kotlin
- Jetpack Compose
- Android Gradle Plugin
- Room
- Retrofit
- OkHttp
- Kotlin Coroutines
- Material 3

### متطلبات البناء

- JDK 17
- Android SDK 36
- Gradle Wrapper

## ⚙️ GitHub Actions

يتم بناء APK تلقائيًا عند:

```text
push → main
```

ويمكن تشغيل البناء يدويًا من:

```text
GitHub
→ Actions
→ Build Android APK
→ Run workflow
```

بعد نجاح البناء يتم:

1. إنشاء APK.
2. تسميته `AI-Content-Factory.apk`.
3. رفعه كـ GitHub Actions Artifact.
4. إنشاء/تحديث Release باسم `latest`.
5. توفير رابط تحميل مباشر من README.

## 📦 Backend

الـBackend مبني باستخدام FastAPI ويوفر API لإدارة:

- Projects
- Jobs
- Assets
- Batches
- Scheduling
- Rendering
- Quality Control
- Publishing
- Media Processing

## 🧪 الاختبارات

قبل اعتبار المشروع جاهزًا للإنتاج، يوصى بتشغيل:

```bash
./gradlew test
```

وبناء التطبيق:

```bash
./gradlew :app:assembleDebug
```

## 🔐 ملاحظات الأمان

لا تضع داخل Git:

- API Keys
- Passwords
- Keystores
- Firebase credentials
- Production secrets

استخدم GitHub Secrets عند الحاجة.

## 📄 الترخيص

راجع إعدادات الترخيص في المستودع قبل التوزيع التجاري.

## 🔗 Repository

urlGitHub Repositoryhttps://github.com/1AhmadEgy/AI-Content-Factory
