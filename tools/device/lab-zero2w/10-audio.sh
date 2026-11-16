#!/bin/sh
# Audio graph for the lab Pi Zero 2 W: PipeWire + WirePlumber as user services.
# Lingering must be on first: sudo loginctl enable-linger "$USER"
set -eu

systemctl --user enable --now pipewire.socket pipewire.service \
  pipewire-pulse.socket wireplumber.service

mkdir -p "$HOME/.config/pipewire/pipewire.conf.d"
cat > "$HOME/.config/pipewire/pipewire.conf.d/99-debra.conf" <<'EOF'
# Debra lab: one fixed clock rate so voice capture at 16 kHz and music at
# 44.1/48 kHz are resampled here instead of renegotiating the codec.
context.properties = {
    default.clock.rate = 48000
    default.clock.allowed-rates = [ 48000 ]
}
EOF

systemctl --user restart pipewire.service wireplumber.service
sleep 2

echo "--- server ---"
pactl info | sed -n '1,6p'
echo "--- sinks ---"
pactl list short sinks
echo "--- sources ---"
pactl list short sources
echo
echo "The WM8960 HAT should be the only sink and source on this board."
echo "If the default is wrong:  wpctl status  /  wpctl set-default <id>"
