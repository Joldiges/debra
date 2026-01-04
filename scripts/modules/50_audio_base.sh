#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"


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
