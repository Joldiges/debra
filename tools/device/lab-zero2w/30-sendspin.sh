#!/bin/sh
# Sendspin player, pinned, as a systemd user service sharing the PipeWire session.
# Requires libportaudio2 from the distribution: the client exits with
# "PortAudio library not found" without it.
#
# Usage: SENDSPIN_VERSION=9.1.0 30-sendspin.sh
set -eu
VERSION="${SENDSPIN_VERSION:-9.1.0}"
HERE=$(cd "$(dirname "$0")" && pwd)

if [ ! -x "$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
"$HOME/.local/bin/uv" tool install "sendspin==$VERSION"

mkdir -p "$HOME/.config/sendspin" "$HOME/lab"
cat > "$HOME/.config/sendspin/settings-daemon.json" <<'EOF'
{
  "name": "Debra Zero 2 W",
  "listen_port": 8928,
  "use_mpris": false,
  "unpaired_access": true,
  "manufacturer": "Debra",
  "product_name": "Pi Zero 2 W + ReSpeaker 2-Mics HAT v1",
  "log_level": "INFO"
}
EOF

install -m 0644 "$HERE/sendspin.service" "$HOME/.config/systemd/user/sendspin.service"
systemctl --user daemon-reload
systemctl --user enable --now sendspin.service
sleep 8
systemctl --user is-active sendspin.service
tail -5 "$HOME/lab/sendspin.log" 2>/dev/null || true
