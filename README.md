🤖 AI Content Factory

منصة Android متقدمة لإنشاء وإدارة المحتوى بالاعتماد على تقنيات الذكاء الاصطناعي، مع بنية قابلة للتوسع، اختبارات آلية، وتجهيزات CI/CD للبناء والإصدار.

✨ المميزات

- 🤖 إنشاء المحتوى باستخدام الذكاء الاصطناعي.
- 📝 إدارة وتحرير المحتوى.
- 🔥 تكامل Firebase.
- 🌐 دعم واجهات API عبر Retrofit و OkHttp.
- ⚡ Kotlin Coroutines.
- 🎨 واجهة حديثة باستخدام Jetpack Compose.
- 🧪 اختبارات Unit Tests و Robolectric.
- 📸 دعم اختبارات واجهة المستخدم والـ screenshots عبر Roborazzi.
- 🔐 إدارة الأسرار ومتغيرات البيئة بدون تخزين المفاتيح الحساسة داخل المستودع.
- 🚀 GitHub Actions للبناء والاختبار والإصدار.
- 📦 إنشاء APK تلقائياً.
- 📱 إمكانية إرسال إشعارات WhatsApp عند اكتمال عمليات CI/CD.

---

🏗️ التقنيات المستخدمة

التقنية| الاستخدام
Kotlin| لغة التطوير الأساسية
Jetpack Compose| بناء واجهة المستخدم
Android SDK 36| منصة البناء
Kotlin Coroutines| العمليات غير المتزامنة
Retrofit| الاتصال بالـ APIs
OkHttp| HTTP Client
Moshi| JSON Serialization
Firebase| خدمات Google/Firebase
Robolectric| اختبارات Android المحلية
Roborazzi| Screenshot Testing
Gradle Kotlin DSL| نظام البناء
GitHub Actions| CI/CD

---

📋 المتطلبات

قبل تشغيل المشروع تأكد من توفر:

- Android Studio حديث.
- JDK 17.
- Android SDK 36.
- Git.
- اتصال بالإنترنت لتحميل dependencies.

---

🚀 تشغيل المشروع

استنسخ المستودع:

git clone https://github.com/1AhmadEgy/AI-Content-Factory.git
cd AI-Content-Factory

ثم افتح المشروع باستخدام Android Studio.

بناء Debug APK

Linux / macOS:

./gradlew assembleDebug

Windows:

.\gradlew.bat assembleDebug

سيتم إنشاء APK داخل:

app/build/outputs/apk/debug/

---

🧪 تشغيل الاختبارات

لتشغيل اختبارات الوحدة:

./gradlew testDebugUnitTest

لتشغيل الاختبارات مع تقرير مفصل:

./gradlew testDebugUnitTest --stacktrace

لتشغيل فحص المشروع:

./gradlew lintDebug

---

🤖 Robolectric

المشروع يستخدم Robolectric لتشغيل اختبارات Android المحلية بدون الحاجة إلى تشغيل Emulator في كل اختبار.

يمكن تشغيل الاختبارات بواسطة:

./gradlew testDebugUnitTest

وتوجد إعدادات الاختبارات داخل:

app/build.gradle.kts

اختبارات Robolectric تكون عادة داخل:

app/src/test/

---

📸 Screenshot Testing

يستخدم المشروع Roborazzi لاختبارات ومقارنة صور واجهة المستخدم.

لتشغيل الاختبارات المرتبطة بـ Roborazzi:

./gradlew testDebugUnitTest

وتبعاً للاختبار المستخدم يمكن إنشاء أو تحديث screenshots بواسطة مهام Gradle الخاصة بـ Roborazzi.

---

🔐 إدارة الأسرار

لا تقم أبداً برفع المفاتيح السرية أو ملفات keystore إلى GitHub.

يمكن استخدام:

.env

للقيم المحلية، مع الاعتماد على:

.env.example

كقالب.

أمثلة على الأسرار

STORE_PASSWORD
KEY_PASSWORD
KEYSTORE_PATH

ويجب تخزين الأسرار الخاصة بـ GitHub Actions داخل:

GitHub → Settings → Secrets and variables → Actions

---

📱 WhatsApp Notifications

يمكن للمشروع إرسال إشعارات WhatsApp من GitHub Actions عند اكتمال عمليات البناء أو الإصدار.

يمكن استخدام خدمة خارجية مثل CallMeBot للإشعارات البسيطة، أو WhatsApp Cloud API من Meta للحلول الإنتاجية.

مثال للأسرار المطلوبة

WHATSAPP_PHONE
WHATSAPP_APIKEY

لا تضع API Key داخل الكود أو README أو ملفات Git.

إذا لم يتم إعداد أسرار WhatsApp، يجب أن تستمر عملية CI/CD بشكل طبيعي بدون فشل البناء بسبب الإشعار.

---

🚀 CI/CD

يتم تنفيذ عمليات البناء والاختبار بواسطة:

.github/workflows/

يشمل الـ pipeline عادة:

1. Checkout للمشروع.
2. إعداد JDK.
3. إعداد Android SDK.
4. تحميل Gradle dependencies.
5. تشغيل Unit Tests.
6. تشغيل Robolectric.
7. تشغيل Lint.
8. بناء Debug APK.
9. بناء Release APK عند إنشاء Tag.
10. توقيع Release APK عند توفر أسرار التوقيع.
11. رفع APK كـ GitHub Artifact.
12. إنشاء GitHub Release.
13. إرسال إشعار WhatsApp عند اكتمال العملية.

---

🏷️ إنشاء Release

لإنشاء إصدار رسمي، استخدم Tag يبدأ بـ:

v

مثال:

git tag v1.0.0
git push origin v1.0.0

وسيتم تشغيل Workflow الخاص بالإصدار تلقائياً.

---

📦 ملفات البناء

Debug

app/build/outputs/apk/debug/

Release

app/build/outputs/apk/release/

يتم رفع ملفات APK الناتجة إلى GitHub Actions Artifacts، ويمكن للإصدارات الرسمية إرفاقها مع GitHub Release.

---

🔒 التوقيع

يجب توفير Keystore آمن للإصدارات الرسمية.

المتغيرات المستخدمة في إعداد التوقيع:

KEYSTORE_PATH
STORE_PASSWORD
KEY_PASSWORD

ولا يجب تخزين:

*.jks
*.keystore

داخل Git.

---

📁 بنية المشروع

AI-Content-Factory/
│
├── app/
│   ├── src/
│   │   ├── main/
│   │   ├── test/
│   │   └── androidTest/
│   │
│   ├── build.gradle.kts
│   └── proguard-rules.pro
│
├── gradle/
│   └── libs.versions.toml
│
├── .github/
│   └── workflows/
│
├── .env.example
├── .gitignore
├── build.gradle.kts
├── settings.gradle.kts
├── gradlew
├── gradlew.bat
└── README.md

---

🧰 أوامر Gradle مفيدة

تنظيف المشروع:

./gradlew clean

بناء Debug:

./gradlew assembleDebug

تشغيل Unit Tests:

./gradlew testDebugUnitTest

تشغيل Lint:

./gradlew lintDebug

عرض جميع مهام Gradle:

./gradlew tasks

تنظيف وإعادة البناء:

./gradlew clean assembleDebug

---

🛡️ الأمان

يرجى الالتزام بالقواعد التالية:

- لا ترفع API Keys.
- لا ترفع Firebase credentials الحساسة.
- لا ترفع Keystore.
- لا تضع كلمات المرور داخل ملفات Gradle.
- استخدم GitHub Secrets في CI/CD.
- استخدم ".env.example" للقيم المطلوبة فقط بدون أسرار حقيقية.
- راجع الملفات قبل تنفيذ "git push".

---

🤝 المساهمة

للمساهمة في المشروع:

git checkout -b feature/my-feature

ثم قم بالتعديلات وشغّل:

./gradlew testDebugUnitTest
./gradlew lintDebug
./gradlew assembleDebug

بعد التأكد من نجاح الاختبارات:

git add .
git commit -m "feat: improve content factory"
git push origin feature/my-feature

ثم أنشئ Pull Request.

---

📄 الترخيص

يرجى الرجوع إلى ملفات المشروع لمعرفة الترخيص المطبق على الإصدار الحالي.

---

📌 حالة المشروع

المشروع قيد التطوير المستمر، ويتم تحسين:

- البنية الداخلية.
- الأداء.
- الاختبارات.
- استقرار CI/CD.
- تجربة المستخدم.
- التكامل مع خدمات الذكاء الاصطناعي.
- نظام الإشعارات.
- آلية الإصدارات والتوقيع.

---

⭐ دعم المشروع

إذا وجدت المشروع مفيداً، يمكنك دعم التطوير عبر إعطاء المستودع ⭐ على GitHub.

AI Content Factory — Build, Test, Automate.