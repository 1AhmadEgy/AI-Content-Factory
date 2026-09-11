# AI Content Factory — Backend / Media Engine

The backend is the authoritative orchestration boundary for long-running content-generation and media work. Android remains a control client; heavy AI, FFmpeg and QC work stay on the backend/worker side.

See `REAL_ONLY_RUNTIME_POLICY.md` for the mandatory production rule: no fake, simulated, placeholder, dry-run, or fabricated success is allowed.

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
- `app/publishing/adapters.py` — provider-agnostic publishing contract backed by configured real HTTP publishing endpoints; missing configuration is an explicit failure.
- `app/scheduling/scheduler.py` — durable JSON development scheduler with batch enqueue, cancellation, retry and recovery semantics.
- `app/security/media_security.py` — path traversal protection, asset hashing and HMAC signing primitives.

## Runtime requirements

For real rendering hosts, install both `ffmpeg` and `ffprobe` and keep them on the worker `PATH`. The renderer uses staging files and never exposes a partially written output as final media.

Real AI providers must be configured explicitly through the documented provider endpoints/models. Real publishing endpoints must likewise be configured explicitly. Missing providers, executables, credentials, endpoints, source assets, or required capabilities must fail closed rather than producing substitute output.

## Completion rule

A render is not complete merely because FFmpeg exits successfully. Final acceptance requires an existing output, successful FFprobe inspection, duration/profile validation and a full decode pass. Provenance is recorded only for accepted output.

Publishing is successful only after the configured external service confirms publication and returns an external identifier. There is no production dry-run publishing path.

Android should consume API/worker state for the Control Center rather than running FFmpeg locally.
