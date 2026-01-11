#!/usr/bin/env bash
set -euo pipefail

# Source common libraries
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"
# shellcheck source=../lib/ui.sh
source "${SCRIPT_DIR}/../lib/ui.sh"

# Prompt to enable Sendspin
if ! prompt_yesno 'Install/enable Sendspin receiver? (experimental)' 'no'; then
  echo "Skipping Sendspin installation."
  exit 0
fi

wget https://raw.githubusercontent.com/Sendspin/sendspin-cli/main/scripts/systemd/install-systemd.sh -O /tmp/install-sendspin.sh
# Have SendSpin use piwheels and local builds.  Neither will break anything if not on a Raspberry Pi.
sudo sed -i \
's|bash -l -c "uv tool install sendspin"|bash -l -c "uv tool install sendspin --index-url https://pypi.org/simple --extra-index-url https://www.piwheels.org/simple --find-links file:///home/'"$USER"'/git/debra/legacy/raspi0/wheels"|' \
chmod +x /tmp/install-sendspin.sh
/tmp/install-sendspin.sh
sudo bash /tmp/install-sendspin.sh
rm /tmp/install-sendspin.sh

