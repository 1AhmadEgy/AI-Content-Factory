# 🤖 AI Content Factory

AI Content Factory هو نظام إنتاج محتوى آلي يبدأ من الفكرة أو القصة، ثم يحولها إلى مشاريع وحلقات ومشاهد ولقطات وأصول صوتية وبصرية، مع QC واختيار أفضل Take وتجميع الناتج النهائي.

**مهم:** مسار الإنتاج لم يعد يعتمد على بيانات تجريبية أو ملفات Media وهمية. التوليد الإنتاجي يتطلب مزود AI حقيقي، والرندر الإنتاجي يتم بواسطة FFmpeg/FFprobe.

---

## 🚀 التشغيل الإنتاجي

1. انسخ `.env.example` إلى `.env`.
2. ضع `OPENAI_API_KEY` في بيئة الخادم فقط.
3. اضبط النماذج عبر `AICF_TEXT_MODEL` و`AICF_IMAGE_MODEL` و`AICF_TTS_MODEL` عند الحاجة.
4. ثبّت FFmpeg وFFprobe.
5. شغّل الـBackend.
6. استخدم تطبيق Android كواجهة تحكم؛ لا يقوم بإنشاء بيانات Demo تلقائيًا.

التفاصيل الكاملة في `PRODUCTION_PROVIDER_SETUP.md`.

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

## 📱 Android

التطبيق مبني باستخدام Kotlin وJetpack Compose وRoom وRetrofit وOkHttp وCoroutines وMaterial 3.

### متطلبات البناء

- JDK 17
- Android SDK 36
- Gradle Wrapper

### اتصال الـBackend من الهاتف

عنوان `10.0.2.2` يعمل مع **Android Emulator فقط** ولا يعمل للوصول إلى جهاز الكمبيوتر من هاتف حقيقي. لذلك لم يعد هذا العنوان قيمة افتراضية في المشروع.

من **Control Center → Backend connection** أدخل عنوان الخادم الذي يستطيع الهاتف الوصول إليه، مثل:

```text
http://192.168.1.10:8000/
```

يتم حفظ العنوان محليًا، وإعادة إنشاء عميل Retrofit عند تغييره، مع اختبار الاتصال مباشرة من شاشة Control Center. يجب أن يكون FastAPI مستمعًا على واجهة يمكن للهاتف الوصول إليها، وليس `127.0.0.1` فقط.

---

## ⚙️ GitHub Actions

يتم بناء APK تلقائيًا عند تحديث `main`، ويمكن تشغيل البناء يدويًا من GitHub Actions.

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

## 📄 الترخيص

راجع إعدادات الترخيص في المستودع قبل التوزيع التجاري.
