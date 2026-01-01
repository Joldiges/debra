#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"

export DEBIAN_FRONTEND=noninteractive

apt-get install -y --no-install-recommends snapclient

cat >/etc/default/snapclient <<EOF
# Managed by Debra
SNAPCLIENT_OPTS="--host ${SNAPSERVER_HOST} --port ${SNAPSERVER_PORT} --player alsa"
EOF

systemctl enable --now snapclient
