#!/bin/sh
# Install the audio-path health check and its timer.
#
# systemd already restarts a service that dies. What it cannot see is a stack
# that is running perfectly and making no sound: on 2026-11-15 every service was
# active, the sink existed, the volume was up, and the codec's line output gain
# was zero. This check tests the path, not the process list, and re-applies the
# known-good mixer when the line gain has gone to zero.
set -eu

mkdir -p "$HOME/.local/bin" "$HOME/.config/systemd/user"

cat > "$HOME/.local/bin/debra-health" <<'EOF'
#!/bin/sh
# Debra lab health check: the audio path, not just the service state.
set -u
C=seeed2micvoicec
fail=0
log() { echo "debra-health: $*"; }

for u in pipewire pipewire-pulse wireplumber linux-voice-assistant sendspin; do
  systemctl --user is-active --quiet "$u" || {
    log "$u inactive, restarting"
    systemctl --user restart "$u" >/dev/null 2>&1 || true
    fail=1
  }
done

sink=$(pactl get-default-sink 2>/dev/null || true)
if [ -z "$sink" ]; then
  log "no default sink"; fail=1
else
  vol=$(pactl get-sink-volume "$sink" 2>/dev/null | sed -n "1s/.*\/ *\([0-9]*\)%.*/\1/p")
  mute=$(pactl get-sink-mute "$sink" 2>/dev/null | awk '{print $2}')
  [ "${vol:-0}" -gt 0 ] 2>/dev/null || { log "sink volume is ${vol:-unknown}%"; fail=1; }
  [ "${mute:-no}" = "no" ] || { log "sink is muted"; fail=1; }
fi

# The HAT's speaker is on the codec's LINE output, measured 2026-11-15.
# A zero gain here is silent while everything else looks healthy.
line=$(amixer -c $C cget name="Line DAC Playback Volume" 2>/dev/null | sed -n "s/.*: values=\([0-9]*\).*/\1/p")
if [ -z "$line" ] || [ "$line" -eq 0 ]; then
  log "line output gain is ${line:-unknown}: re-applying the known-good mixer"
  amixer -c $C sset "Line DAC" 106 >/dev/null 2>&1
  amixer -c $C sset "Line" 3 >/dev/null 2>&1
  sudo -n alsactl store >/dev/null 2>&1 || true
  fail=1
fi

[ "$fail" -eq 0 ] || log "repaired something; see the lines above"
exit 0
EOF
chmod +x "$HOME/.local/bin/debra-health"

cat > "$HOME/.config/systemd/user/debra-health.service" <<'EOF'
[Unit]
Description=Debra lab audio and service health check

[Service]
Type=oneshot
ExecStart=%h/.local/bin/debra-health
EOF

cat > "$HOME/.config/systemd/user/debra-health.timer" <<'EOF'
[Unit]
Description=Run the Debra lab health check every two minutes

[Timer]
OnBootSec=90s
OnUnitActiveSec=2min
AccuracySec=15s

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now debra-health.timer
sleep 1
systemctl --user is-active debra-health.timer
"$HOME/.local/bin/debra-health" && echo "health check: clean"
