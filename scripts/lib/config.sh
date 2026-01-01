#!/usr/bin/env bash
set -euo pipefail

write_config() {
  local cfg="$1"; shift
  mkdir -p "$(dirname "${cfg}")"
  touch "${cfg}"
  chmod 600 "${cfg}"

  for kv in "$@"; do
    local key="${kv%%=*}"
    local val="${kv#*=}"

    grep -v -E "^${key}=" "${cfg}" > "${cfg}.tmp" || true
    mv "${cfg}.tmp" "${cfg}"
    echo "${key}=${val}" >> "${cfg}"
  done
}
