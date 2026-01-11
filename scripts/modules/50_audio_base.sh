#!/usr/bin/env bash
set -euo pipefail

# Source common libraries
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

## TODO:
# sudo nano /boot/firmware/config.txt
# dtparam=i2s=on
# #dtparam=audio=on


# Conservative default: allow multiple playback streams via dmix.
tee /etc/asound.conf <<'EOF'
pcm.!default {
  type plug
  slave.pcm "hw:0,0"
}

ctl.!default {
  type hw
  card 0
}
EOF
