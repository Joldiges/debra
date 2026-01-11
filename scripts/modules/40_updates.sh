#!/usr/bin/env bash
set -euo pipefail

# Source common library
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

require_root
detect_distro

if [[ "$IS_DEBIAN_LIKE" -eq 0 && "$IS_FEDORA_LIKE" -eq 0 ]]; then
  echo "Skipping: unsupported distro '$DISTRO_ID'."
  exit 0
fi

# Prompt (interactive) or skip (non-interactive) unless explicitly enabled via env var
enable="${ENABLE_AUTO_UPDATES:-0}"
if [[ "$enable" != "1" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "Enable automatic updates (Sundays at 02:00)? [y/N] " ans
    ans="${ans:-N}"
    [[ "$ans" =~ ^[Yy]$ ]] && enable=1
  else
    echo "Non-interactive run: skipping (set ENABLE_AUTO_UPDATES=1 to enable)."
    exit 0
  fi
fi

if [[ "$enable" != "1" ]]; then
  echo "No changes made."
  exit 0
fi

if [[ "$IS_DEBIAN_LIKE" -eq 1 ]]; then
  export DEBIAN_FRONTEND=noninteractive

  apt-get update
  apt-get install -y --no-install-recommends unattended-upgrades apt-listchanges

  cat >/etc/systemd/system/unattended-upgrades-sunday.service <<'EOF'
[Unit]
Description=Unattended upgrades (weekly)

[Service]
Type=oneshot
ExecStart=/usr/bin/bash -c '/usr/bin/apt-get update && /usr/bin/unattended-upgrade -v'
EOF

  cat >/etc/systemd/system/unattended-upgrades-sunday.timer <<'EOF'
[Unit]
Description=Run unattended upgrades Sundays at 02:00

[Timer]
OnCalendar=Sun *-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

  systemctl daemon-reload
  systemctl enable --now unattended-upgrades-sunday.timer

  echo "Enabled weekly updates (Sun 02:00) on Debian/Ubuntu."
  exit 0
fi

if [[ "$IS_FEDORA_LIKE" -eq 1 ]]; then
  command -v dnf >/dev/null 2>&1 || { echo "Skipping: dnf not found."; exit 0; }

  dnf -y install dnf-automatic

  cat >/etc/dnf/automatic.conf <<'EOF'
[commands]
upgrade_type = default
download_updates = yes
apply_updates = yes
random_sleep = 0

[emitters]
emit_via = stdio
EOF

  timer_unit=""
  while read -r unit _; do
    case "$unit" in
      dnf-automatic-install.timer|dnf-automatic.timer) timer_unit="$unit"; break;;
    esac
  done < <(systemctl list-unit-files --type=timer --no-legend --no-pager)

  if [[ -z "$timer_unit" ]]; then
    echo "Installed dnf-automatic, but no dnf-automatic*.timer unit found to enable."
    exit 1
  fi

  mkdir -p "/etc/systemd/system/${timer_unit}.d"
  cat >"/etc/systemd/system/${timer_unit}.d/override.conf" <<'EOF'
[Timer]
OnCalendar=
OnCalendar=Sun *-*-* 02:00:00
RandomizedDelaySec=0
EOF

  systemctl daemon-reload
  systemctl enable --now "$timer_unit"

  echo "Enabled weekly automatic updates on Fedora/RHEL-like (Sun 02:00) via $timer_unit."
  exit 0
fi
