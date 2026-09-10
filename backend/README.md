# AI Content Factory — Backend / Media Engine

The backend is the authoritative orchestration boundary for long-running content-generation and media work. Android remains a control client; heavy AI, FFmpeg and QC work stay on the backend/worker side.

## Implemented media path

```text
Timeline + immutable asset paths
        ↓
FFmpeg render (staging)
        ↓
FFprobe + full decode QC
        ↓
Thumbnail extraction
        ↓
Metadata sidecar
        ↓
SHA-256 provenance manifest
        ↓
Immutable final artifact
```

### Real media components

- `app/rendering/ffmpeg_renderer.py` — real FFmpeg execution, deterministic input ordering, H.264/AAC MP4 output, audio mixing, cancellation and FFprobe access.
- `app/rendering/media_qc.py` — actual FFprobe inspection plus full decode validation before acceptance.
- `app/rendering/media_artifacts.py` — SRT subtitles, real frame thumbnails, metadata and SHA-256 provenance.
- `app/rendering/pipeline.py` — render → QC gate → thumbnail → metadata → provenance finalization.
- `app/rendering/repurpose.py` — vertical, square and horizontal output profiles for repurposing.
- `app/publishing/adapters.py` — provider-agnostic publishing contract with a safe dry-run adapter.
- `app/scheduling/scheduler.py` — durable JSON development scheduler with batch enqueue, cancellation, retry and recovery semantics.
- `app/security/media_security.py` — path traversal protection, asset hashing and HMAC signing primitives.

## Runtime requirements

For real rendering hosts, install both `ffmpeg` and `ffprobe` and keep them on the worker `PATH`. The renderer uses staging files and never exposes a partially written output as final media.

## Completion rule

A render is not complete merely because FFmpeg exits successfully. Final acceptance requires an existing output, successful FFprobe inspection, duration/profile validation and a full decode pass. Provenance is recorded only for accepted output.

Publishing adapters are intentionally isolated from rendering and orchestration. Real platform adapters should be added behind `PublishingAdapter`; the default adapter is dry-run and does not publish externally.

Android should consume API/worker state for the Control Center rather than running FFmpeg locally.
