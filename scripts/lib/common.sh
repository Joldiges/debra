#!/usr/bin/env bash
# Common functions and variables for Debra scripts
# Source this file at the top of your script

# Prevent double-sourcing
[[ -n "${_DEBRA_COMMON_SOURCED:-}" ]] && return 0
_DEBRA_COMMON_SOURCED=1

set -euo pipefail

# --- Project Root ---
# Derive PROJECT_ROOT from git, fallback to script location
if command -v git &>/dev/null && git rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
  PROJECT_ROOT="$(git rev-parse --show-toplevel)"
else
  # Fallback: assume common.sh is in scripts/lib/
  PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
fi
export PROJECT_ROOT

# --- Script directories ---
DEBRA_SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
DEBRA_LIB_DIR="${DEBRA_SCRIPTS_DIR}/lib"
DEBRA_MODULES_DIR="${DEBRA_SCRIPTS_DIR}/modules"
export DEBRA_SCRIPTS_DIR DEBRA_LIB_DIR DEBRA_MODULES_DIR

# --- Logging ---
say() { echo -e "==> $*"; }
warn() { echo -e "!!  $*" >&2; }
die() { echo -e "ERR $*" >&2; exit 1; }

# --- Require root ---
require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "Run as root (sudo)."
  fi
}

# --- Run a module script ---
run_module() {
  local mod="$1"; shift
  if [[ ! -x "${mod}" ]]; then
    chmod +x "${mod}" || true
  fi
  say "\n\n\n\n\n"
  say "Running module: $(basename "${mod}")"
  bash "${mod}" "$@"
}

# --- Platform detection ---
detect_platform() {
  DEBRA_PLATFORM="linux"

  if [[ -f /proc/device-tree/model ]] && grep -qi "raspberry pi" /proc/device-tree/model; then
    DEBRA_PLATFORM="raspberrypi"
    return
  fi

  if [[ -f /sys/firmware/devicetree/base/model ]] && grep -qi "raspberry pi" /sys/firmware/devicetree/base/model; then
      DEBRA_PLATFORM="raspberrypi"
    fi


  export DEBRA_PLATFORM
}

# --- Identity ---
# Lazy-load DEBRA_ID and DEBRA_HOSTNAME
get_debra_id() {
  if [[ -z "${DEBRA_ID:-}" ]]; then
    DEBRA_ID="$("${DEBRA_SCRIPTS_DIR}/python/get_unique_id.py" --short 6)"
    export DEBRA_ID
  fi
  echo "${DEBRA_ID}"
}

get_debra_hostname() {
  if [[ -z "${DEBRA_HOSTNAME:-}" ]]; then
    DEBRA_HOSTNAME="debra-$(get_debra_id)"
    export DEBRA_HOSTNAME
  fi
  echo "${DEBRA_HOSTNAME}"
}

# --- Distro detection ---
detect_distro() {
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    source /etc/os-release
  else
    DISTRO_ID="unknown"
    DISTRO_LIKE=""
    IS_DEBIAN_LIKE=0
    IS_FEDORA_LIKE=0
    export DISTRO_ID DISTRO_LIKE IS_DEBIAN_LIKE IS_FEDORA_LIKE
    return
  fi

  DISTRO_ID="${ID:-unknown}"
  DISTRO_LIKE="${ID_LIKE:-}"

  IS_DEBIAN_LIKE=0
  IS_FEDORA_LIKE=0

  if [[ "$DISTRO_ID" == "debian" || "$DISTRO_ID" == "ubuntu" || "$DISTRO_LIKE" == *"debian"* ]]; then
    IS_DEBIAN_LIKE=1
  elif [[ "$DISTRO_ID" == "fedora" || "$DISTRO_LIKE" == *"fedora"* || "$DISTRO_LIKE" == *"rhel"* ]]; then
    IS_FEDORA_LIKE=1
  fi

  export DISTRO_ID DISTRO_LIKE IS_DEBIAN_LIKE IS_FEDORA_LIKE
}

