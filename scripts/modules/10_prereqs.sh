#!/usr/bin/env bash
set -euo pipefail

# Source common library
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates curl wget git \
  ccache \
  python3 python3-venv python3-pip \
  alsa-utils

if [ "$(uname -m)" = "armv6l" ]; then
  cat >/etc/pip.conf <<EOF
[global]
extra-index-url=https://www.piwheels.org/simple
index-url = https://pypi.org/simple
find-links = file:///${PROJECT_ROOT}/legacy/raspi0/wheels
EOF
fi  # The wheels are specifically for the Pi 0 W (V1), but won't hurt to include them on other Raspi models.



# Install and enable avahi-daemon for network service discovery (mDNS/Zeroconf)
apt-get install -y --no-install-recommends avahi-daemon
systemctl enable --now avahi-daemon

# Install and enable chrony for time synchronization better than systemd-timesyncd
apt-get install -y --no-install-recommends chrony
systemctl enable --now chrony || systemctl enable --now chronyd || true
