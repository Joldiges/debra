#!/usr/bin/env bash
set -euo pipefail

# TODO: Make `ps1` and `sh` versions aligned with some config or something.  Most people won't want pwsh on Linux.

IMAGE_NAME="raspbian-trixie-wheel-shell"

# Resolve repo root (three levels up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Enable qemu binfmt for ARM
docker run --privileged --rm tonistiigi/binfmt --install arm >/dev/null

# Buildx builder (idempotent)
if ! docker buildx inspect raspbian >/dev/null 2>&1; then
  docker buildx create --name raspbian --use >/dev/null
fi
docker buildx inspect --bootstrap >/dev/null

# Build image (Dockerfile is in this folder)
docker buildx build \
  --platform linux/arm/v6 \
  -t "$IMAGE_NAME" \
  --load \
  "$SCRIPT_DIR"

# Enter interactive shell with repo root mounted
docker run --rm -it \
  --platform linux/arm/v6 \
  -e QEMU_CPU=arm1176 \
  -v "$REPO_ROOT:/work" \
  "$IMAGE_NAME"
