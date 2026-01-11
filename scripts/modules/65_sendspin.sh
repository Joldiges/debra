#!/usr/bin/env bash
set -euo pipefail

# Prompt helpers
prompt_yesno() {
  local label="$1"
  local default="${2:-no}" # yes/no
  local prompt="[y/N]"
  [[ "${default}" == "yes" ]] && prompt="[Y/n]"

  while true; do
    read -r -p "${label} ${prompt}: " ans
    ans="$(echo "${ans}" | tr '[:upper:]' '[:lower:]')"
    if [[ -z "${ans}" ]]; then
      [[ "${default}" == "yes" ]] && return 0 || return 1
    fi
    case "${ans}" in
      y|yes) return 0 ;;
      n|no)  return 1 ;;
      *) echo "Answer yes or no." ;;
    esac
  done
}

# Prompt to enable Sendspin
if ! prompt_yesno 'Install/enable Sendspin receiver? (experimental)' 'no'; then
  echo "Skipping Sendspin installation."
  exit 0
fi

wget https://raw.githubusercontent.com/Sendspin/sendspin-cli/main/scripts/systemd/install-systemd.sh -O /tmp/install-sendspin.sh
# Have SendSpin use piwheels and local builds.  Neither will break anything if not on a Raspberry Pi.
sudo sed -i \
's|bash -l -c "uv tool install sendspin"|bash -l -c "uv tool install sendspin --index-url https://pypi.org/simple --extra-index-url https://www.piwheels.org/simple --find-links file:///home/'"$USER"'/git/debra/legacy/raspi0/wheels"|' \
/tmp/install-sendspin.sh
sudo bash /tmp/install-sendspin.sh
rm /tmp/install-sendspin.sh

