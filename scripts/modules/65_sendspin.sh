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
  apt-get install -y --no-install-recommends python3.13-dev libopenblas0 pkg-config ffmpeg libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libavfilter-dev libswscale-dev libswresample-dev
elif [[ "$IS_FEDORA_LIKE" -eq 1 ]]; then
  dnf install -y openblas pkgconf-pkg-config ffmpeg ffmpeg-devel
else
  warn "Unknown distro '$DISTRO_ID' - cannot install OpenBLAS automatically"
  return 1
fi

# TODO: Not sure which is actually needed - but one worked to multithread the build for numpy\
export NPY_NUM_BUILD_JOBS="$(nproc)"
export MAKEFLAGS="-j$(nproc)"
export CMAKE_BUILD_PARALLEL_LEVEL="$(nproc)"


wget https://raw.githubusercontent.com/Sendspin/sendspin-cli/main/scripts/systemd/install-systemd.sh -O /tmp/install-sendspin.sh
if [ "$(uname -m)" = "armv6l" ]; then
    sudo sed -i \
's|bash -l -c "uv tool install sendspin"|bash -l -c "uv tool install sendspin --index-url https://pypi.org/simple --extra-index-url https://www.piwheels.org/simple --find-links file://'"${PROJECT_ROOT}"'/legacy/raspi0/wheels" -- --only-binary=:all:|' \
/tmp/install-sendspin.sh
else
    sudo sed -i \
's|bash -l -c "uv tool install sendspin"|bash -l -c "uv tool install sendspin -- --only-binary=:all:|' \
/tmp/install-sendspin.sh
fi

chmod +x /tmp/install-sendspin.sh
bash /tmp/install-sendspin.sh
rm /tmp/install-sendspin.sh

