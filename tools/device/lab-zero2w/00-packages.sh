#!/bin/sh
# Distribution packages this device build needs and the web/setup installers
# deliberately do not install. Run once on a fresh card; it is idempotent.
#
# Usage: sudo 00-packages.sh    (or run as the user and let sudo prompt)
set -eu

if [ "$(id -u)" -ne 0 ]; then
  exec sudo -- "$0" "$@"
fi

apt-get update
apt-get install -y \
  git \
  avahi-utils \
  libportaudio2 \
  libmpv2 \
  python3-venv \
  python3-dev \
  libasound2-plugins \
  build-essential

echo "packages installed; avahi-browse is what the web page's discovery needs"
command -v avahi-browse >/dev/null
