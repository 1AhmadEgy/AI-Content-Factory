# 🤖 AI Content Factory

AI Content Factory هو نظام إنتاج محتوى آلي يبدأ من الفكرة أو القصة، ثم يحولها إلى مشاريع وحلقات ومشاهد ولقطات وأصول صوتية وبصرية، مع QC واختيار أفضل Take وتجميع الناتج النهائي.

**مهم:** مسار الإنتاج لا يعتمد على بيانات تجريبية أو ملفات Media وهمية. التوليد الإنتاجي يتطلب مزود AI حقيقي، والرندر الإنتاجي يتم بواسطة FFmpeg/FFprobe.

---

## 🚀 التشغيل الإنتاجي

1. انسخ `.env.example` إلى `.env`.
2. ضع `OPENAI_API_KEY` في بيئة الخادم فقط.
3. اضبط النماذج عبر `AICF_TEXT_MODEL` و`AICF_IMAGE_MODEL` و`AICF_TTS_MODEL` عند الحاجة.
4. ثبّت FFmpeg وFFprobe.
5. شغّل الـBackend.
6. استخدم تطبيق Android كواجهة تحكم؛ لا يقوم بإنشاء بيانات Demo تلقائيًا.

راجع `PRODUCTION_PROVIDER_SETUP.md` لتفاصيل مزودي الإنتاج.

إذا لم توجد بيانات اعتماد المزود، لا يتم إنشاء ناتج وهمي؛ يفشل الطلب بوضوح بدل الادعاء بأنه اكتمل.

---

## 🏗️ Architecture

```text
Android App
     │
     │ REST API
     ▼
  FastAPI
     │
     ├── Projects / Series / Episodes
     ├── Durable Jobs + Queue
     ├── Real AI Providers
     ├── Assets + Provenance
     ├── QC + Best Take
     ├── Timeline
     ├── FFmpeg / FFprobe
     └── Publishing
            │
            ▼
        Final MP4
```

## 📚 Documentation

الوثائق الفنية المنظمة موجودة داخل `docs/specifications/`، وتشمل API والعقود وقاعدة البيانات والـQueue والـWorkers والـProviders والـAssets والـQC والـTimeline والنشر.

خارطة الإصلاح والتقوية: `REPAIR_ROADMAP.md`.

---

## 📱 Android

التطبيق مبني باستخدام Kotlin وJetpack Compose وRoom وRetrofit وOkHttp وCoroutines وMaterial 3.

### متطلبات البناء

- JDK 17
- Android SDK 36
- Gradle Wrapper

## ⚙️ GitHub Actions

- `android-apk.yml`: فحص وبناء APK للـPR و`main`.
- `ci.yml`: اختبارات Backend وفحص Docker والنشر إلى GHCR عند الدمج إلى `main`.
- `release-apk.yml`: إصدار APK موقّع للإنتاج باستخدام GitHub Environment `production`.
- `unzip-fixes.yml`: استيراد ZIPs المرفوعة إلى فرع مراجعة مستقل، دون الكتابة المباشرة إلى `main`.

## 📦 Backend

الـBackend مبني باستخدام FastAPI ويوفر API لإدارة Projects وJobs وAssets وScheduling وRendering وQC وPublishing وMedia Processing.

## 🧪 الاختبارات

```bash
./gradlew test
cd backend
pytest
```

وبناء Android:

```bash
./gradlew :app:assembleDebug
```

## 🔐 الأمان

لا تضع داخل Git أي API Keys أو كلمات مرور أو Keystores أو بيانات اعتماد الإنتاج. استخدم متغيرات البيئة وGitHub Secrets.

الـAndroid هو Control Plane؛ أسرار مزودي AI يجب أن تبقى على الخادم ولا تُضمّن داخل APK الإنتاجي.

## 📄 الترخيص

راجع إعدادات الترخيص في المستودع قبل التوزيع التجاري.
