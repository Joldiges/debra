#!/bin/sh
# Linux Voice Assistant, pinned to a release tag, as a systemd user service.
# It must run as the same user that owns the PipeWire session.
#
# Usage: LVA_TAG=v1.1.18 20-lva.sh
set -eu
TAG="${LVA_TAG:-v1.1.18}"
DIR="$HOME/linux-voice-assistant"
HERE=$(cd "$(dirname "$0")" && pwd)

if [ ! -d "$DIR/.git" ]; then
  git clone --depth 1 --branch "$TAG" \
    https://github.com/OHF-Voice/linux-voice-assistant.git "$DIR"
fi
cd "$DIR"
chmod +x docker-entrypoint.sh
git describe --tags --always > "$DIR/.pinned-version"

# script/setup rebuilds .venv from scratch, so only run it when it is absent.
if [ ! -x "$DIR/.venv/bin/linux-voice-assistant" ]; then
  ./script/setup --cxxflags="-O1 -g0" --makeflags="-j2"
fi

mkdir -p "$HOME/.config/systemd/user" "$HOME/lab"
install -m 0644 "$HERE/linux-voice-assistant.service" \
  "$HOME/.config/systemd/user/linux-voice-assistant.service"

systemctl --user daemon-reload
systemctl --user enable --now linux-voice-assistant.service
sleep 5
systemctl --user is-active linux-voice-assistant.service
tail -5 "$HOME/lab/lva.log" 2>/dev/null || true
echo "Home Assistant discovers this satellite over ESPHome on port 6053."
