# AI Content Factory — Technical Specification

هذه الوثيقة تحتوي على المواصفات التقنية الصارمة والقواعد المعمارية التي يجب أن يتبعها أي مهندس أو نظام ذكاء اصطناعي (Codex/AI Agents) يعمل على هذا المشروع.

## 1. Core Contracts

### 1.1 Result Wrapper
كل العمليات الأساسية تستخدم نتيجة موحدة لمنع نشر الاستثناءات (Exceptions) عشوائياً:
```kotlin
sealed interface Result<out T> {
    data class Success<T>(val data: T) : Result<T>
    data class Failure(val error: AppError) : Result<Nothing>
}
```

### 1.2 AppError
تصنيف واضح للأخطاء:
`Validation`, `Network`, `Persistence`, `Provider`, `Worker`, `Qc`, `License`, `Hardware`, `Unknown`.

## 2. Repository & Use Cases

- **Repository**: الـ UI لا يتعامل مع Room مباشرة. يتم تعريف واجهات (Interfaces) مثل `ProjectRepository`, `GenerationJobRepository` إلخ.
- **Use Cases**: لا يحتوي `ViewModel` على منطق المصنع. يتم استخدام Use Cases مثل `GenerateStoryUseCase`, `QueueGenerationJobUseCase`.

## 3. Database Schema & Relations

- **الجداول الأساسية**: `projects`, `series`, `episodes`, `characters`, `locations`, `scenes`, `shots`, `generation_jobs`, `assets` وغيرها.
- **الروابط**: Project -> Series -> Episode -> Scene -> Shot. الشخصيات ترتبط بـ Series.

## 4. Job Engine & Queue Scheduler

- **GenerationJob**: يحتوي على `targetId`, `status`, `progress`, `provider`, `model`, `input`, `output`, `error`, `priority`.
- **Job Dependency Graph**: لا يبدأ Job إلا إذا اكتملت الـ Dependencies (مثال: LipSync ينتظر Video و Voice).
- **Scheduler**: يختار الـ Job بناءً على: Status, Priority, Dependencies, Hardware compatibility.
- **Retry Policy**: إعادة المحاولة للأخطاء القابلة للتدارك (Network, Busy) وعدم الإعادة لأخطاء (Invalid Input, License).

## 5. Worker Interface & Fallback

- **Worker Interface**:
```kotlin
interface GenerationWorker {
    val type: JobType
    suspend fun execute(job: GenerationJob): WorkerResult
}
```
- **Fallback**: Local Provider -> Failure -> Alternative Local -> Cloud (إذا كان مسموحاً).
- **Health Check**: يجب أن يبلغ كل Worker عن حالته (ONLINE, BUSY, OFFLINE).

## 6. Prompt & Continuity System

- **Prompt Builder**: لا يكتب الـ Worker الـ Prompt. يتم بناؤه عبر `PromptBuilder` يجمع (Character Bible + World + Camera + Constraints).
- **Continuity Engine**: يحذر من التناقضات بين المشاهد (تغير ملابس الشخصية بدون سبب).

## 7. QC Engine & Best Take

- **QC Engine**: تقييم المخرجات (Resolution, Duration, Face Consistency, Audio). ينتج `PASS / FAIL / REGENERATE`.
- **Best Take**: اختيار المحاولة (Take) الأفضل بناءً على QC Score.

## 8. Rendering & Assets

- **Timeline Engine**: بناء Tracks (Video, Audio, Subtitle) وتحويلها لخطة `FFmpeg`.
- **Asset Provenance**: كل ملف يتم تسجيل مصدره بدقة (Hash, Model, Prompt, Source Assets) لضمان التتبع والترخيص.

## 9. Hardware & License Guard

- **Hardware Detector**: يفحص العتاد (VRAM, RAM, GPU) لمنع إرسال مهام تفوق قدرة الجهاز.
- **License Guard**: التحقق من ترخيص النموذج قبل التشغيل (`VERIFIED`, `UNKNOWN`, `RESTRICTED`, `BLOCKED`).

## 10. Strict Development Rules (Codex / AI Agents)

1. **Inspect before editing**: اقرأ الملفات دائمًا قبل التعديل.
2. **Never rewrite from scratch**: لا تعد كتابة المشروع بالكامل بدون سبب.
3. **Domain Independence**: لا تربط UI بـ Providers مباشرة، ولا تضع AI Logic في Compose.
4. **No delay() for Production**: الـ Mock يجب أن ينتج Asset حقيقي (Deterministic) وليس مجرد `delay()`.
5. **No Secrets in Repo**: لا تضع API Keys أو Credentials في الكود أبداً.
6. **Tests First**: لا تضف ميزات جديدة قبل إصلاح Build/Tests. إضافة Tests مع كل Core feature.
7. **Small Commits**: اجعل التعديلات صغيرة، قابلة للاختبار والتراجع.

## 11. End-to-End Mock (Sprint 1 Goal)

يجب أن ينجح هذا المسار بالكامل **بدون** AI حقيقي أو GPU قبل الانتقال للخطوة التالية:
`Create Project` -> `Create Episode` -> `Story` -> `Characters` -> `Scenes` -> `Shots` -> `Queue` -> `Mock Workers` -> `Assets` -> `QC` -> `Timeline` -> `Mock Render` -> `Final MP4`.
