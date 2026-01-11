#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

# Prompt helpers
prompt_string() {
  local label="$1"
  local default="${2:-}"
  local val=""
  if [[ -n "${default}" ]]; then
    read -r -p "${label} [${default}]: " val
    echo "${val:-${default}}"
  else
    read -r -p "${label}: " val
    echo "${val}"
  fi
}

# Prompt for snapserver configuration
SNAPSERVER_HOST="$(prompt_string 'Snapserver host/IP (usually Music Assistant host)' 'homeassistant.local')"
SNAPSERVER_PORT="$(prompt_string 'Snapserver port (snapclient stream port)' '1704')"

apt-get install -y --no-install-recommends snapclient

cat >/etc/default/snapclient <<EOF
# Managed by Debra
SNAPCLIENT_OPTS="--host ${SNAPSERVER_HOST} --port ${SNAPSERVER_PORT} --player alsa"
EOF

systemctl enable --now snapclient
