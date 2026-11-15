#!/bin/sh
# Reduce the Pi 5's peak current so a marginal supply is less likely to brown out.
#
# This is mitigation, not a fix. A sagging 5V rail is a hardware fault: the SoC
# resets mid-work and the microSD card is at risk. The reliable fix is a supply
# rated for 5V/5A with USB-C PD (the official 27W supply) and a short, thick cable.
set -eu

# 1. Keep the journal across boots. Without this, the evidence of a brownout
#    disappears with the boot that caused it.
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal
sudo systemctl restart systemd-journald

# 2. Cap the CPU and pin the governor. A 1.5 GHz ceiling is ample for PipeWire,
#    wake-word detection and a Sendspin player, and it removes the top-end
#    current spike that a marginal supply trips on.
sudo tee /etc/systemd/system/debra-powercap.service >/dev/null <<'EOF'
[Unit]
Description=Cap Raspberry Pi 5 CPU frequency (Debra lab)

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'for p in /sys/devices/system/cpu/cpufreq/policy*; do \
  echo powersave > "$p/scaling_governor" 2>/dev/null || true; \
  echo 1500000 > "$p/scaling_max_freq" 2>/dev/null || true; done'

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now debra-powercap.service

# 3. Docker is installed but the lab Music Assistant container is not used while
#    the household Music Assistant (HA add-on) is the music source. Do not start
#    the daemon at boot; the container can be started by hand when wanted.
if command -v docker >/dev/null 2>&1; then
  sudo systemctl disable docker.socket docker.service 2>/dev/null || true
fi

echo "--- governor / max freq ---"
for p in /sys/devices/system/cpu/cpufreq/policy*; do
  printf '%s %s %s\n' "$p" "$(cat "$p/scaling_governor")" "$(cat "$p/scaling_max_freq")"
done
echo "--- docker boot state ---"
systemctl is-enabled docker.service 2>/dev/null || true
echo "--- journal persistent? ---"
[ -d /var/log/journal ] && echo "yes: /var/log/journal"
