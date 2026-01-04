#!/usr/bin/env bash
set -euo pipefail

say() { echo -e "==> $*"; }
warn() { echo -e "!!  $*" >&2; }
die() { echo -e "ERR $*" >&2; exit 1; }

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    die "Run as root (sudo)."
  fi
}

run_module() {
  local mod="$1"; shift
  if [[ ! -x "${mod}" ]]; then
    chmod +x "${mod}" || true
  fi
  say "\n\n\n\n\n"
  say "Running module: $(basename "${mod}")"
  bash "${mod}" "$@"
}

detect_platform() {
  DEBRA_PLATFORM="linux"

  if [[ -f /proc/device-tree/model ]] && grep -qi "raspberry pi" /proc/device-tree/model; then
    DEBRA_PLATFORM="raspberrypi"
    return
  fi

  if [[ -f /sys/firmware/devicetree/base/model ]] && grep -qi "raspberry pi" /sys/firmware/devicetree/base/model; then
    DEBRA_PLATFORM="raspberrypi"
  fi
}

