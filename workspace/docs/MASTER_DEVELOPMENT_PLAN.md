# AI Content Factory — Master Development & Recovery Plan

المشروع: AI Content Factory
Repository: 1AhmadEgy/AI-Content-Factory
الهدف: بناء منصة إنتاج فيديو بالذكاء الاصطناعي Local-first، قابلة للعمل Offline/Local GPU، مع Cloud اختياري، وتدعم الإنتاج الفردي والجماعي والسلاسل.

---

## 1. الرؤية النهائية

المشروع ليس مجرد تطبيق Android لإنشاء فيديو.
بل:
> نظام تشغيل لمصنع محتوى AI.

المدخل: فكرة
المخرج: فيديو جاهز للنشر

والخط الكامل:
Idea → Story → Characters → World → Scenes → Shots → Dialogue → Voice → Images → Video → Lip Sync → Music / SFX → QC → Best Take → Timeline → Subtitles → Render → Publishing Package → Analytics → Learning

---

## 2. المبدأ المعماري الأساسي

يجب الفصل الكامل بين:
- **CONTROL**: Android (وظيفته Control Center، وليس AI Compute Engine)
- **PRODUCTION**: Backend (وظيفته Orchestration, API, Queue, State, Security, Scheduling)
- **WORKERS**: (وظيفتهم AI Processing, Rendering, Media Processing)

---

## 3. البنية النهائية

```text
AI-Content-Factory/
│
├── android/
├── backend/
├── workers/
├── models/
├── infrastructure/
├── scripts/
├── docs/
├── tests/
└── README.md
```

---

## 4. Android Architecture

```text
android/
└── app/
    └── src/main/java/com/aistudio/aicontentfactory/
        ├── core/ (common, result, error, logging, network)
        ├── domain/ (model, repository, usecase)
        ├── data/ (local, remote, mapper, repository)
        └── feature/ (dashboard, projects, series, episodes, characters, worlds, scenes, shots, assets, production, queue, qc, analytics, settings)
```

---

## 5. Domain Model النهائي

يجب أن يصبح لدينا نموذج موحد للمصنع:
- **Project**: id, name, description, mode, status, settings, timestamps
- **Series**: projectId, title, genre, language, styleBible, continuityRules
- **Season**: seriesId, number, title, description
- **Episode**: seasonId, number, title, synopsis, script, status

---

## 6. Character System

الشخصية يجب أن تبقى ثابتة عبر الحلقات.
- **Character**: id, seriesId, name, age, personality, appearance, clothing, voiceProfile, referenceAssets, negativeConstraints, metadata
- **CharacterAsset**: characterId, assetId, type, version

---

## 7. World / Location System

- **World**: visualStyle, colorPalette, lightingRules, consistencyRules
- **Location**: worldId, name, description, references, cameraRules, lighting

---

## 8. Scene System

- **Scene**: episodeId, number, locationId, description, emotion, characters, dialogue, duration, shots

---

## 9. Shot System

هذه الطبقة مهمة جدًا.
- **Shot**: sceneId, number, duration, framing, camera, lens, movement, lighting, action, emotion, characters, prompt, negativePrompt, status

---

## 10. Dialogue System

- **Dialogue**: shotId, characterId, text, language, emotion, voiceId, duration, audioAssetId, lipSyncAssetId

---

## 11. Asset System

كل شيء ينتجه النظام يصبح Asset.
- **Asset**: id, projectId, type, path, mimeType, size, width, height, duration, hash, provider, model, prompt, source, createdAt, metadata
أنواع الـ Assets: IMAGE, VIDEO, AUDIO, VOICE, MUSIC, SFX, SUBTITLE, PROJECT_FILE, FINAL_VIDEO

---

## 12. Generation Job Engine

الـ Job Engine هو قلب المصنع.
- **GenerationJob**: id, type, targetType, targetId, priority, status, progress, attempt, maxAttempts, provider, model, input, output, error, createdAt, startedAt, completedAt, metadata
الحالات: CREATED, QUEUED, RUNNING, PAUSED, RETRYING, COMPLETED, FAILED, CANCELLED

---

## 13. Retry / Fallback

أي Worker يمكن أن يفشل.
Worker → Failure → Retry → Failure → Fallback → Alternative Model

---

## 14. Production Modes

ثلاثة أوضاع رسمية:
1. **MOCK**: للتطوير والاختبار (No real AI, No GPU, No cloud)
2. **LOCAL**: Local GPU, Local Models, Local Workers
3. **CLOUD**: External Provider
لاحقاً: HYBRID (Local → Cloud fallback)

---

## 15. Model Registry

كل نموذج يجب تسجيله.
- **Model**: id, name, version, category, provider, local, cloud, hardwareRequirements, qualityScore, speedScore, license, enabled
الفئات: LLM, IMAGE, VIDEO, TTS, LIPSYNC, MUSIC, SFX, UPSCALE, TRANSCRIPTION

---

## 16. Hardware Detection

النظام يفحص العتاد المتاح (CPU, RAM, GPU, VRAM, CUDA, ROCm, Disk, OS) وبناءً عليه يحدد النماذج المتوافقة.

---

## 17. Model Router

يقرر النموذج الأفضل بناءً على المهمة، الجودة، العتاد، الترخيص، السرعة، والتكلفة.

---

## 18. Story Agent

يحول فكرة المستخدم إلى: Story, Characters, World, Scenes, Dialogue بصيغة Structured JSON.

---

## 19. Character Agent

يستخرج Character Bible ويمنع التناقضات لتوريثها في الـ Prompts اللاحقة.

---

## 20. Director Agent

يحوّل Scene إلى Shots مع تحديد Composition, Camera, Blocking, Lighting, Performance, Pacing.

---

## 21. Image Worker

واجهة موحدة: ImageGenerationProvider (يدعم ComfyUI, FLUX, وغيرها).

---

## 22. Video Worker

واجهة: VideoGenerationProvider (يدعم Wan وغيرها).

---

## 23. TTS Worker

واجهة: TTSProvider (مثل Piper وغيرها، مع تحقق من التراخيص).

---

## 24. Lip Sync Worker

Audio + Character Video → Lip Sync → Output Video.

---

## 25. Music / SFX

فصل الموسيقى والمؤثرات عن الحوار لتدمج في الـ Timeline.

---

## 26. QC Engine

File Validation, Duration, Resolution, Codec, Audio, Video Integrity, Face Consistency, Character Consistency, Lip Sync, Prompt Compliance.
النتيجة: QCResult (score, passed, errors, warnings, metrics).

---

## 27. Best Take Selector

يتم تقييم عدة محاولات للمشهد واختيار الأفضل بناءً على QC Score.

---

## 28. Timeline Engine

Timeline (tracks, transitions, effects) يتحول إلى خطة تنفيذ لـ FFmpeg.

---

## 29. Render Engine

Timeline → Render Planner → FFmpeg → Validation → Final Asset.

---

## 30. Subtitle Engine

يستخرج النص من Dialogue ويدعم (SRT, ASS, VTT, Burn-in).

---

## 31. Queue Engine

يدعم Priority, Concurrency, Retry, Pause, Resume, Cancel, Dependencies, Worker selection.

---

## 32. Dependency Graph

Story → Characters → Scenes → Shots → Voice → Video → LipSync → QC → Render.
تغيير في شخصية يؤثر فقط على المشاهد والأصول المرتبطة بها.

---

## 33. Content Memory

يحتفظ بمعلومات الشخصيات والأماكن والأسلوب للمواسم والحلقات القادمة.

---

## 34. Continuity Engine

ينبه لأي تناقض في ظهور الشخصيات أو الأماكن أو الخط الزمني.

---

## 35. Batch Factory

يدعم إنتاج حلقات متعددة دفعة واحدة مع إدارة الموارد والاولويات.

---

## 36. Resource Manager

إدارة الـ VRAM والـ GPU لمنع الانهيار بناءً على متطلبات النماذج.

---

## 37. Analytics

يسجل أوقات المعالجة والموارد والمقاييس لتقييم الأداء والتكلفة.

---

## 38. Learning Loop

يستخدم البيانات التاريخية لاقتراح أفضل إعدادات للنماذج.

---

## 39. License Guard

يتحقق من تراخيص النماذج قبل تشغيلها ويمنع استخدام الممنوعة (BLOCKED).

---

## 40. Security

حماية بيانات الدخول ومفاتيح الـ API ومنع تخزينها في GitHub.

---

## 41. Observability

تتبع كامل للعمليات من الـ Project وصولاً للـ Asset والـ QC باستخدام Logs و IDs.

---

## 42. Testing Strategy

Unit Tests, Integration Tests, End-to-End Tests.

---

## 43. Mock Mode

استخدام Mock Workers حقيقية تنتج أصولاً ثابتة للاختبار دون حاجة لـ GPU.

---

## 44. CI/CD

GitHub Actions للتحقق من جودة الكود والبناء قبل أي دمج.

---

## 45. Documentation

إنشاء وثائق شاملة لكل جزء من المشروع في مجلد `docs/`.

---

## 46. مراحل الإصدار

- **v0.1 — Foundation**: Build, Tests, Architecture, Room, Domain, Repository, Jobs, Mock Worker
- **v0.2 — Production Core**: Queue, Dependencies, Retry, Assets, QC, Timeline, Render
- **v0.3 — AI Story Factory**: Story Agent, Character Agent, Scene Planner, Shot Planner
- **v0.4 — Local AI**: Ollama, ComfyUI, Local Image/Video/TTS, Lip Sync
- **v0.5 — Complete Video Pipeline**: Story → Shots → Video → Audio → LipSync → QC → Render
- **v0.6 — Factory**: Batch, Series Memory, Continuity, Resource Manager
- **v0.7 — Intelligence**: Best Take, Analytics, Learning Loop, Model Router
- **v1.0 — Production**: Stable, Tested, Documented, Local-first, Cloud optional, Plugin-ready

---

## 47. ما لن نفعله

- ❌ إعادة كتابة المشروع بالكامل بدون سبب.
- ❌ وضع كل المنطق في Repository.
- ❌ وضع AI logic داخل Compose.
- ❌ تشغيل النماذج الثقيلة داخل Android.
- ❌ استخدام delay() لمحاكاة Production.
- ❌ إعلان Job ناجحًا بدون Asset.
- ❌ إضافة Provider مباشرة إلى UI.
- ❌ ربط النظام بنموذج AI واحد.
- ❌ الاعتماد على Cloud فقط.
- ❌ تخزين API Keys في GitHub.
- ❌ تجاهل تراخيص النماذج.
- ❌ إضافة ميزات جديدة قبل إصلاح Build/Test.

---

## 48. ترتيب التنفيذ الإجباري

01 Build Health → 02 Package Cleanup → 03 Architecture → 04 Domain Models → 05 Room → 06 Repository → 07 Job Engine → 08 Mock Workers → 09 Queue → 10 Asset System → 11 QC → 12 Timeline → 13 Renderer → 14 Backend → 15 Orchestrator → 16 Story Agent → 17 Character Bible → 18 World Memory → 19 Scene Planner → 20 Shot Planner → 21 Local LLM → 22 Image Worker → 23 Video Worker → 24 TTS → 25 LipSync → 26 Music/SFX → 27 Full Pipeline → 28 Batch Factory → 29 Continuity → 30 Analytics → 31 Learning → 32 Model Router → 33 License Guard → 34 Plugin System → 35 Optional Cloud → 36 v1.0

---

## 49. أول هدف قابل للقياس

لا نعتبر المشروع تقدمًا حقيقيًا حتى يستطيع تنفيذ:
Create Project → Create Series → Create Episode → Enter Story → Generate Story Plan → Create Characters → Create Scenes → Create Shots → Queue Jobs → Mock Workers → QC → Timeline → Render → Final MP4
بدون تدخل يدوي.

---

## 50. Definition of Done

Code + Tests + Error Handling + Logging + Persistence + Documentation
لـ AI Providers: Provider Adapter + Model Registry + Job + Asset + Error Handling + Retry + QC + Tests
