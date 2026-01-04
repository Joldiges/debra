#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
# shellcheck source=lib/ui.sh
source "${SCRIPT_DIR}/lib/ui.sh"
# shellcheck source=lib/config.sh
source "${SCRIPT_DIR}/lib/config.sh"

require_root
detect_platform

say "Debra setup starting on: $(hostname)  (platform: ${DEBRA_PLATFORM})"

CFG_DIR="/etc/debra"
CFG_FILE="${CFG_DIR}/debra.conf"
mkdir -p "${CFG_DIR}"

# Load existing config if present
if [[ -f "${CFG_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${CFG_FILE}"
fi

say ""
say "Core settings"
# TODO: Move configs to their respective modules.  (or make them a function and only called if needed..?)
SNAPSERVER_HOST="${SNAPSERVER_HOST:-$(prompt_string 'Snapserver host/IP (usually Music Assistant host)' 'homeassistant.local')}"
SNAPSERVER_PORT="${SNAPSERVER_PORT:-$(prompt_string 'Snapserver port (snapclient stream port)' '1704')}"

ENABLE_SENDSPIN="${ENABLE_SENDSPIN:-$(prompt_yesno 'Install/enable Sendspin receiver too? (experimental)' 'yes' && echo 1 || echo 0)}"
SENDSPIN_URL="${SENDSPIN_URL:-}"
if [[ "${ENABLE_SENDSPIN}" == "1" ]]; then
  SENDSPIN_URL="$(prompt_string 'Sendspin server URL (blank = auto-discovery via mDNS)' '')"
fi

ENABLE_UNATTENDED="${ENABLE_UNATTENDED:-$(prompt_yesno 'Enable unattended SECURITY updates?' 'yes' && echo 1 || echo 0)}"
ENABLE_WEEKLY_REBOOT="${ENABLE_WEEKLY_REBOOT:-$(prompt_yesno 'Weekly reboot timer?' 'no' && echo 1 || echo 0)}"

ENABLE_RESPEAKER="${ENABLE_RESPEAKER:-0}"
if [[ "${DEBRA_PLATFORM}" == "raspberrypi" ]]; then
  ENABLE_RESPEAKER="$(prompt_yesno 'Install ReSpeaker/Seeed voicecard drivers? (Pi only)' 'yes' && echo 1 || echo 0)"
fi

say ""
say "Voice satellite (Linux Voice Assistant)"
# TODO: Add local models and default to them.  Debra.
LVA_WAKE_MODEL="${LVA_WAKE_MODEL:-$(prompt_string 'Wake model id' 'okay_nabu')}"
LVA_AUDIO_INPUT="${LVA_AUDIO_INPUT:-$(prompt_string 'Audio INPUT device (blank = auto/default)' '')}"
LVA_AUDIO_OUTPUT="${LVA_AUDIO_OUTPUT:-$(prompt_string 'Audio OUTPUT device (blank = auto/default)' '')}"

# --- Unique ID + hostname ---
DEBRA_ID="$("${SCRIPT_DIR}/python/get_unique_id.py" --short 6)"
DEBRA_HOSTNAME="debra-${DEBRA_ID}"

say ""
say "Identity"
say " - Unique ID: ${DEBRA_ID}"
say " - Hostname:   ${DEBRA_HOSTNAME}"

# --- Write config early ---
write_config "${CFG_FILE}" \
  "DEBRA_PLATFORM=${DEBRA_PLATFORM}" \
  "DEBRA_ID=${DEBRA_ID}" \
  "SNAPSERVER_HOST=${SNAPSERVER_HOST}" \
  "SNAPSERVER_PORT=${SNAPSERVER_PORT}" \
  "ENABLE_SENDSPIN=${ENABLE_SENDSPIN}" \
  "SENDSPIN_URL=${SENDSPIN_URL}" \
  "ENABLE_UNATTENDED=${ENABLE_UNATTENDED}" \
  "ENABLE_WEEKLY_REBOOT=${ENABLE_WEEKLY_REBOOT}" \
  "ENABLE_RESPEAKER=${ENABLE_RESPEAKER}" \
  "LVA_WAKE_MODEL=${LVA_WAKE_MODEL}" \
  "LVA_AUDIO_INPUT=${LVA_AUDIO_INPUT}" \
  "LVA_AUDIO_OUTPUT=${LVA_AUDIO_OUTPUT}"

say ""
say "User setup"

# NEW_USER="${NEW_USER:-$(prompt_string 'Create a new sudo username' 'debra')}"
# NEW_PASS="$(prompt_secret 'Password for the new user')"
NEW_USER="${NEW_USER:-$(prompt_string 'Create a new sudo username' "${SUDO_USER:-$(id -un)}")}"
say "User is: ${NEW_USER}"
NEW_PASS="${NEW_PASS:-$(prompt_string 'password....' 'N/A')}"


# LOCK_DEFAULT_USER="$(prompt_yesno 'Lock the default user account after verification?' 'no' && echo 1 || echo 0)"
# write_config "${CFG_FILE}" "NEW_USER=${NEW_USER}" "LOCK_DEFAULT_USER=${LOCK_DEFAULT_USER}"

# --- Run modules ---
run_module "${REPO_DIR}/scripts/modules/10_prereqs.sh" "${CFG_FILE}"
run_module "${REPO_DIR}/scripts/modules/20_user.sh" "${CFG_FILE}" "${NEW_USER}" "${NEW_PASS}"
run_module "${REPO_DIR}/scripts/modules/30_hostname.sh" "${CFG_FILE}"
run_module "${REPO_DIR}/scripts/modules/40_updates.sh" "${CFG_FILE}"
run_module "${REPO_DIR}/scripts/modules/50_audio_base.sh" "${CFG_FILE}"

if [[ "${ENABLE_RESPEAKER}" == "1" ]]; then
  run_module "${REPO_DIR}/scripts/modules/55_respeaker.sh" "${CFG_FILE}"
fi

run_module "${REPO_DIR}/scripts/modules/60_snapcast.sh" "${CFG_FILE}"
if [[ "${ENABLE_SENDSPIN}" == "1" ]]; then
  run_module "${REPO_DIR}/scripts/modules/65_sendspin.sh" "${CFG_FILE}"
fi

run_module "${REPO_DIR}/scripts/modules/70_linux_voice_assistant.sh" "${CFG_FILE}" "${NEW_USER}"
run_module "${REPO_DIR}/scripts/modules/99_finish.sh" "${CFG_FILE}"

say ""
say "Done. Reboot is recommended."
if prompt_yesno "Reboot now?" "yes"; then
  reboot
else
  say "Reboot later with: sudo reboot"
fi
