# Production Provider Setup

AI Content Factory no longer treats synthetic generation or fake media manifests as production output. Production generation requires a configured real provider and production rendering requires FFmpeg/FFprobe.

## 1. Environment

Copy `.env.example` to `.env` and configure:

```text
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
AICF_TEXT_MODEL=gpt-5.6-luna
AICF_IMAGE_MODEL=gpt-image-2
AICF_TTS_MODEL=gpt-4o-mini-tts
RUNWAYML_API_SECRET=...
ELEVENLABS_API_KEY=...
AICF_ELEVENLABS_TTS_MODEL=eleven_multilingual_v2
AICF_ELEVENLABS_VOICE_ID=...
AICF_RUNWAY_VIDEO_MODEL=gen4.5
AICF_FFMPEG_BIN=ffmpeg
AICF_FFPROBE_BIN=ffprobe
```

Never commit the API key.

## 2. Real provider behavior

- Story/script/scene/shot planning uses the configured OpenAI text model.
- Image jobs use the configured OpenAI image model and persist the returned image bytes as a real asset.
- TTS jobs use the configured OpenAI speech model and persist the returned audio bytes.
- Video jobs can use Runway Dev (`gen4.5`) when `RUNWAYML_API_SECRET` is configured; the adapter submits an async task, polls it, downloads the ephemeral result URL, and persists the video as a local asset.
- TTS jobs can use ElevenLabs (`eleven_multilingual_v2`) when `ELEVENLABS_API_KEY` and `AICF_ELEVENLABS_VOICE_ID` are configured. Arabic text is supported; the voice itself determines accent/pronunciation, so an Arabic/Egyptian-trained voice should be selected for Egyptian dialogue.
- Provider errors fail the job with a structured error; the system does not silently fabricate a result.
- If no provider key is configured, the production registry is empty and generation fails explicitly with `AI_PROVIDER_UNAVAILABLE`.

## 3. Real rendering

All production rendering goes through `FfmpegRenderer`. A missing FFmpeg/FFprobe installation is a hard error. The previous deterministic manifest renderer has been removed from the production rendering contract.

Final output is accepted only after the existing render/QC path verifies a real media file.

## 4. Android

The Android client no longer creates a fake demo project on first launch and no longer submits `mock-deterministic` jobs. Scene generation requests the real OpenAI image model through the backend.

## 5. Provider model selection

Override model IDs with environment variables rather than editing source code. The backend routes each provider only when its own credential is present. Runway video routing requires `RUNWAYML_API_SECRET`.

## 6. Local development without provider credentials

The repository may contain deterministic test doubles for unit tests, but they are not registered by the production runtime and must never be used to mark a production job as completed.

### Character voice mapping

Each character may define a provider-specific ElevenLabs voice id in its `voice` profile:

```json
{"voice":{"ttsVoiceId":"<elevenlabs-voice-id>"}}
```

Shot dialogue generation reads that id and creates a TTS job for the speaking character. This keeps one stable voice per character across episodes while allowing different characters to use different voices.
