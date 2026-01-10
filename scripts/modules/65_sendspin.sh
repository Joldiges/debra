#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"

if [[ ${ENABLE_SENDSPIN:-0} != "1" ]]; then
  exit 0
fi

wget https://raw.githubusercontent.com/Sendspin/sendspin-cli/main/scripts/systemd/install-systemd.sh -O /tmp/install-sendspin.sh
# Have SendSpin use piwheels and local builds.  Neither will break anything if not on a Raspberry Pi.
sudo sed -i \
's|bash -l -c "uv tool install sendspin"|bash -l -c "uv tool install sendspin --index-url https://pypi.org/simple --extra-index-url https://www.piwheels.org/simple --find-links file:///home/'"$USER"'/git/debra/legacy/raspi0/wheels"|' \
/tmp/install-sendspin.sh
sudo bash /tmp/install-sendspin.sh
rm /tmp/install-sendspin.sh

