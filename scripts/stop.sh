#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${1:-pm-mvp}"

docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
echo "Stopped $CONTAINER_NAME"
