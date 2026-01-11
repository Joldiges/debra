#!/usr/bin/env bash
set -euo pipefail

# Source common libraries
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"
# shellcheck source=../lib/ui.sh
source "${SCRIPT_DIR}/../lib/ui.sh"

# Prompt to enable Sendspin
if ! prompt_yesno 'Install/enable Sendspin receiver? (experimental)' 'yes'; then
  echo "Skipping Sendspin installation."
  exit 0
fi

# --- Dep Handling ---
detect_distro
if [[ "$IS_DEBIAN_LIKE" -eq 1 ]]; then
  apt-get install -y --no-install-recommends libopenblas0
elif [[ "$IS_FEDORA_LIKE" -eq 1 ]]; then
  dnf install -y openblas
else
  warn "Unknown distro '$DISTRO_ID' - cannot install OpenBLAS automatically"
  return 1
fi


wget https://raw.githubusercontent.com/Sendspin/sendspin-cli/main/scripts/systemd/install-systemd.sh -O /tmp/install-sendspin.sh
# Have SendSpin use piwheels and local builds.  Neither will break anything if not on a Raspberry Pi.
sudo sed -i \
's|bash -l -c "uv tool install sendspin"|bash -l -c "uv tool install sendspin --index-url https://pypi.org/simple --extra-index-url https://www.piwheels.org/simple --find-links file://'"${PROJECT_ROOT}"'/legacy/raspi0/wheels"|' \
/tmp/install-sendspin.sh

chmod +x /tmp/install-sendspin.sh
sudo bash /tmp/install-sendspin.sh
rm /tmp/install-sendspin.sh

