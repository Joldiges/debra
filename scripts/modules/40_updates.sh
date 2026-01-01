#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"

export DEBIAN_FRONTEND=noninteractive

if [[ "${ENABLE_UNATTENDED:-0}" == "1" ]]; then
  apt-get install -y --no-install-recommends unattended-upgrades apt-listchanges

  cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
EOF

  systemctl enable --now unattended-upgrades || true
fi

if [[ "${ENABLE_WEEKLY_REBOOT:-0}" == "1" ]]; then
  cat >/etc/systemd/system/debra-weekly-reboot.service <<'EOF'
[Unit]
Description=Debra weekly reboot

[Service]
Type=oneshot
ExecStart=/usr/sbin/reboot
EOF

  cat >/etc/systemd/system/debra-weekly-reboot.timer <<'EOF'
[Unit]
Description=Debra weekly reboot timer

[Timer]
OnCalendar=Sun *-*-* 03:30:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

  systemctl daemon-reload
  systemctl enable --now debra-weekly-reboot.timer
fi
