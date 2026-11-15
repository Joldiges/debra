#!/bin/sh
# Audio graph for the lab Pi 5: PipeWire + WirePlumber as user services.
# Lingering must be on first: sudo loginctl enable-linger "$USER"
set -eu

systemctl --user enable --now pipewire.socket pipewire.service \
  pipewire-pulse.socket wireplumber.service

mkdir -p "$HOME/.config/pipewire/pipewire.conf.d"
cat > "$HOME/.config/pipewire/pipewire.conf.d/99-debra.conf" <<'EOF'
# Debra lab: one fixed clock rate for the ReSpeaker HAT (symmetric_rate=1) so
# voice capture at 16 kHz and music at 44.1/48 kHz are resampled here instead of
# fighting over the hardware.
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
echo "Set the HAT as the default sink and source, e.g.:"
echo "  wpctl status                      # find the seeed2micvoicec nodes"
echo "  wpctl set-default <sink-id>"
echo "  wpctl set-default <source-id>"
