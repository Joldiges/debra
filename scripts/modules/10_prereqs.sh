#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates curl wget git \
  ccache \
  python3 python3-venv python3-pip \
  alsa-utils \
  avahi-daemon \
  chrony \
  build-essential pkg-config

timedatectl set-timezone "${DEBRA_TIMEZONE}" || true
systemctl enable --now avahi-daemon
systemctl enable --now chrony || systemctl enable --now chronyd || true
