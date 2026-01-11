#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEBRA_ID="$("${SCRIPT_DIR}/../python/get_unique_id.py" --short 6)"
DEBRA_HOSTNAME="debra-${DEBRA_ID}"

# Read snapclient config if available
SNAPSERVER_HOST="(unknown)"
SNAPSERVER_PORT="(unknown)"
if [[ -f /etc/default/snapclient ]]; then
  # Extract host and port from SNAPCLIENT_OPTS
  SNAP_OPTS=$(grep -oP 'SNAPCLIENT_OPTS="\K[^"]+' /etc/default/snapclient 2>/dev/null || true)
  SNAPSERVER_HOST=$(echo "$SNAP_OPTS" | grep -oP '(?<=--host )[^ ]+' || echo "(unknown)")
  SNAPSERVER_PORT=$(echo "$SNAP_OPTS" | grep -oP '(?<=--port )[^ ]+' || echo "(unknown)")
fi

# Check if sendspin is installed
SENDSPIN_INSTALLED=0
if systemctl list-unit-files sendspin.service &>/dev/null; then
  SENDSPIN_INSTALLED=1
fi

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
if [[ "${SENDSPIN_INSTALLED}" == "1" ]]; then
  echo " - systemctl status sendspin"
fi
echo "==============================================="
