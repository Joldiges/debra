#!/bin/sh
# Record the Pi 5 power/throttle flags so an under-voltage fault has evidence.
#
# Raspberry Pi 5 does not "block boot on undervoltage": the firmware reports it
# and the SoC throttles or browns out. What this catches is the difference
# between a stale message and a rail that actually sags under load, which is what
# makes Ethernet/Wi-Fi drop and services restart.
#
# Flags (vcgencmd get_throttled):
#   bit 0  under-voltage now        bit 16 under-voltage has occurred
#   bit 1  arm frequency capped     bit 17 arm frequency capping occurred
#   bit 2  currently throttled      bit 18 throttling occurred
#   bit 3  soft temperature limit   bit 19 soft temperature limit occurred
set -eu
LOG=/var/log/debra-power.log
AGENT=/usr/local/sbin/debra-powerwatch
UNIT=/etc/systemd/system/debra-powerwatch.service
TIMER=/etc/systemd/system/debra-powerwatch.timer

# The agent is a script, not an inline shell: systemd would read the '%' in a
# printf format string as a specifier and refuse the whole unit.
sudo tee "$AGENT" >/dev/null <<EOF
#!/bin/sh
stamp=\$(date -u +%FT%TZ)
flags=\$(vcgencmd get_throttled 2>/dev/null || echo 'throttled=unknown')
up=\$(cut -d' ' -f1 /proc/uptime)
echo "\$stamp \$flags uptime=\$up" >> $LOG
EOF
sudo chmod 0755 "$AGENT"

sudo tee "$UNIT" >/dev/null <<EOF
[Unit]
Description=Record Raspberry Pi power and throttle flags (Debra)

[Service]
Type=oneshot
ExecStart=$AGENT
EOF

sudo tee "$TIMER" >/dev/null <<EOF
[Unit]
Description=Sample Raspberry Pi power flags every 5 minutes and at boot

[Timer]
OnBootSec=20s
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now debra-powerwatch.timer
sudo systemctl start debra-powerwatch.service
sleep 1
echo "--- current flags ---"
vcgencmd get_throttled
echo "--- PMIC rails (A) ---"
vcgencmd pmic_read_adc 2>/dev/null | grep -E "VDD_CORE_A|EXT5V_V|current" | head -6 || true
echo "--- log so far ---"
tail -5 "$LOG" 2>/dev/null || echo "no samples yet"
