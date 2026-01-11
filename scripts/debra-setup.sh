#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"
# shellcheck source=lib/ui.sh
source "${SCRIPT_DIR}/lib/ui.sh"

require_root
detect_platform

say "Debra setup starting on: $(hostname)  (platform: ${DEBRA_PLATFORM})"

# --- Unique ID + hostname ---
DEBRA_ID="$(get_debra_id)"
DEBRA_HOSTNAME="$(get_debra_hostname)"

say ""
say "Identity"
say " - Unique ID: ${DEBRA_ID}"
say " - Hostname:   ${DEBRA_HOSTNAME}"

# --- Run modules (each handles its own prompts) ---
run_module "${DEBRA_MODULES_DIR}/10_prereqs.sh"
#run_module "${DEBRA_MODULES_DIR}/20_user.sh"
run_module "${DEBRA_MODULES_DIR}/30_hostname.sh"
run_module "${DEBRA_MODULES_DIR}/40_updates.sh"
run_module "${DEBRA_MODULES_DIR}/50_audio_base.sh"

# ReSpeaker is only for Raspberry Pi - module will detect and skip if not applicable
if [[ "${DEBRA_PLATFORM}" == "raspberrypi" ]]; then
  if prompt_yesno 'Install ReSpeaker/Seeed voicecard drivers? (Pi only)' 'yes'; then
    run_module "${DEBRA_MODULES_DIR}/55_respeaker.sh"
  fi
fi

run_module "${DEBRA_MODULES_DIR}/60_snapcast.sh"
run_module "${DEBRA_MODULES_DIR}/65_sendspin.sh"
run_module "${DEBRA_MODULES_DIR}/70_linux_voice_assistant.sh"
run_module "${DEBRA_MODULES_DIR}/99_finish.sh"

say ""
say "Done. Reboot is recommended."
if prompt_yesno "Reboot now?" "yes"; then
  reboot
else
  say "Reboot later with: sudo reboot"
fi
