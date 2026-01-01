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

# TODO: Remove.  Timezone to be configured from the imager
timedatectl set-timezone "${DEBRA_TIMEZONE}" || true

# Install and enable avahi-daemon for network service discovery (mDNS/Zeroconf)
apt-get install -y --no-install-recommends avahi-daemon
systemctl enable --now avahi-daemon

# Install and enable chrony for time synchronization
apt-get install -y --no-install-recommends chrony
systemctl enable --now chrony || systemctl enable --now chronyd || true
