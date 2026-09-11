#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is required."
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: Docker Compose v2 is required."
  exit 1
fi

mkdir -p data/assets

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

echo "Starting the real local stack (FastAPI + Ollama + FFmpeg)..."
docker compose -f docker-compose.free.yml up -d --build

echo
echo "Backend: http://127.0.0.1:8000/api/v1/docs"
echo "Health:  http://127.0.0.1:8000/api/v1/health"
echo "Ready:   http://127.0.0.1:8000/api/v1/ready"
echo
echo "No mock/fake provider is enabled. Media generation remains disabled until a real media provider is configured."
echo "Logs: docker compose -f docker-compose.free.yml logs -f backend"
