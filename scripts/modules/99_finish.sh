#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"

echo ""
echo "================ Debra summary ================"
echo "Hostname:   ${DEBRA_HOSTNAME}"
echo ""
echo "Voice (Home Assistant):"
echo " - Add integration: Settings -> Devices & Services -> Add -> ESPHome"
echo " - Choose: Set up another instance of ESPHome"
echo " - Enter: ${DEBRA_HOSTNAME}.local:6053"
echo ""
echo "Music (Snapcast):"
echo " - snapclient -> ${SNAPSERVER_HOST}:${SNAPSERVER_PORT}"
echo ""
echo "Services:"
echo " - systemctl --user status linux-voice-assistant"
echo " - systemctl status snapclient"
if [[ "${ENABLE_SENDSPIN:-0}" == "1" ]]; then
  echo " - systemctl status sendspin"
fi
echo "==============================================="
