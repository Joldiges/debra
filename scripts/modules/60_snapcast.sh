#!/usr/bin/env bash
set -euo pipefail

# Source common libraries
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"
# shellcheck source=../lib/ui.sh
source "${SCRIPT_DIR}/../lib/ui.sh"

export DEBIAN_FRONTEND=noninteractive


# Prompt for snapserver configuration
SNAPSERVER_HOST="$(prompt_string 'Snapserver host/IP (usually Music Assistant host)' 'homeassistant.local')"
SNAPSERVER_PORT="$(prompt_string 'Snapserver port (snapclient stream port)' '1704')"

apt-get install -y --no-install-recommends snapclient

cat >/etc/default/snapclient <<EOF
# Managed by Debra
SNAPCLIENT_OPTS="--host ${SNAPSERVER_HOST} --port ${SNAPSERVER_PORT} --player alsa"
EOF

systemctl enable --now snapclient
