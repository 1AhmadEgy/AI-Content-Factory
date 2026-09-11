# Free Local Runtime

This repository can be run locally without paid AI APIs for the text-generation path by using Ollama. The backend and FFmpeg run locally as well.

## Requirements

- Docker Engine
- Docker Compose v2
- A machine with enough RAM/disk for the selected Ollama model

## Start

```bash
cp .env.example .env
bash scripts/free-local-start.sh
```

The default text model is `llama3.2:3b`. To use another model, set it before startup:

```bash
AICF_TEXT_PROVIDER_MODEL=your-local-ollama-model bash scripts/free-local-start.sh
```

API documentation:

```text
http://127.0.0.1:8000/api/v1/docs
```

## What is real in this stack

- FastAPI backend is real.
- SQLite persistence is real local persistence.
- Ollama text generation is a real local model call.
- Worker and scheduler execution are real.
- FFmpeg/FFprobe media rendering and QC are real.
- Assets are persisted and hashed; success gates require real outputs.
- No mock provider or fabricated success is enabled.

## Important limitation

This free stack does **not** invent a media-generation provider. Image/video/audio generation requires a real local or remote media endpoint compatible with `LocalMediaModelAdapter`.

Configure it with:

```text
AICF_MEDIA_PROVIDER_ENDPOINT
AICF_MEDIA_PROVIDER_MODEL
AICF_MEDIA_PROVIDER_CAPABILITIES
```

The endpoint must return actual bytes or actual text plus a provider run identifier. If it is not configured, media jobs fail explicitly instead of producing placeholder media.

This is intentional and is part of the repository's real-only runtime policy.

## Stop

```bash
docker compose -f docker-compose.free.yml down
```

To remove the downloaded Ollama model data as well:

```bash
docker compose -f docker-compose.free.yml down -v
```
