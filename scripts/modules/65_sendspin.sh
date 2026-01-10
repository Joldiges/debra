#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"

if [[ ${ENABLE_SENDSPIN:-0} != "1" ]]; then
  exit 0
fi

wget https://raw.githubusercontent.com/Sendspin/sendspin-cli/main/scripts/systemd/install-systemd.sh -O /tmp/install-sendspin.sh
sudo bash /tmp/install-sendspin.sh
rm /tmp/install-sendspin.sh

