#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${1:-pm-mvp}"
CONTAINER_NAME="${2:-pm-mvp}"
PORT="${3:-8000}"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker build -t "$IMAGE_NAME" .
docker run -d --name "$CONTAINER_NAME" -p "$PORT:8000" -v pm-data:/app/data --env-file .env "$IMAGE_NAME"
echo "Running at http://127.0.0.1:${PORT}"
