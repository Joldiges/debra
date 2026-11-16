#!/bin/sh
# Linux Voice Assistant on the original Pi Zero W (ARMv6), as a systemd user
# service, with the local ARMv6 workarounds applied.
#
# This is the released upstream tag plus two pinned workarounds that upstream
# has not shipped yet: an ARMv6 libtensorflowlite_c.so, and the stop-word
# gating patch. See README.md for what each one is and when to retire it.
#
# It must run as the same user that owns the PipeWire session. The build is the
# slow step on one core; upstream recommends -j1 for this board and it is the
# default here. If the build is killed for memory, it will need swap or a
# cross-build rather than a higher -j.
#
# Usage: LVA_TAG=v1.1.18 ./20-lva.sh
set -eu

TAG="${LVA_TAG:-v1.1.18}"
DIR="${LVA_DIR:-$HOME/linux-voice-assistant}"
HERE=$(cd "$(dirname "$0")" && pwd)

if [ ! -d "$DIR/.git" ]; then
  git clone --depth 1 --branch "$TAG" \
    https://github.com/OHF-Voice/linux-voice-assistant.git "$DIR"
fi
cd "$DIR"
chmod +x docker-entrypoint.sh
git describe --tags --always > "$DIR/.pinned-version"

# script/setup rebuilds .venv from scratch, so only run it when it is absent.
# The constraints keep pip on versions that actually have armv6l wheels.
if [ ! -x "$DIR/.venv/bin/linux-voice-assistant" ]; then
  install -m 0644 "$HERE/constraints-armv6.txt" "$DIR/constraints-armv6.txt"
  PIP_CONSTRAINT="$DIR/constraints-armv6.txt" \
    ./script/setup --cxxflags="-O1 -g0" --makeflags="${LVA_MAKEFLAGS:--j1}"
fi

"$HERE/21-armv6-tflite.sh"
"$HERE/22-stop-word-gate.sh"

mkdir -p "$HOME/.config/systemd/user" "$HOME/lab"
install -m 0644 "$HERE/linux-voice-assistant.service" \
  "$HOME/.config/systemd/user/linux-voice-assistant.service"

systemctl --user daemon-reload
systemctl --user enable --now linux-voice-assistant.service
sleep 5
systemctl --user is-active linux-voice-assistant.service
tail -5 "$HOME/lab/lva.log" 2>/dev/null || true
echo "Home Assistant discovers this satellite over ESPHome on port 6053."
