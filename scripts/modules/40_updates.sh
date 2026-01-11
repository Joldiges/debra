#!/usr/bin/env bash
set -euo pipefail

# Must be root
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Please run as root (e.g., sudo $0)."
  exit 1
fi

# Detect distro
if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
else
  echo "Skipping: cannot detect distro (missing /etc/os-release)."
  exit 0
fi

distro_id="${ID:-unknown}"
distro_like="${ID_LIKE:-}"

is_debian_like=0
is_fedora_like=0

if [[ "$distro_id" == "debian" || "$distro_id" == "ubuntu" || "$distro_like" == *"debian"* ]]; then
  is_debian_like=1
elif [[ "$distro_id" == "fedora" || "$distro_like" == *"fedora"* || "$distro_like" == *"rhel"* ]]; then
  is_fedora_like=1
fi

if [[ "$is_debian_like" -eq 0 && "$is_fedora_like" -eq 0 ]]; then
  echo "Skipping: unsupported distro '$distro_id'."
  exit 0
fi

read -r -p "Enable unattended automatic updates (Sundays at 02:00)? [y/N] " ans
ans="${ans:-N}"
if [[ ! "$ans" =~ ^[Yy]$ ]]; then
  echo "No changes made."
  exit 0
fi

if [[ "$is_debian_like" -eq 1 ]]; then
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

  echo "Enabled weekly unattended upgrades on Debian/Ubuntu (Sun 02:00). owo"
  exit 0
fi

if [[ "$is_fedora_like" -eq 1 ]]; then
  # Install dnf-automatic
  if command -v dnf >/dev/null 2>&1; then
    dnf -y install dnf-automatic
  else
    echo "Skipping: expected dnf on '$distro_id' but it's not available."
    exit 0
  fi

  # Configure to apply updates automatically
  mkdir -p /etc/dnf
  cat >/etc/dnf/automatic.conf <<'EOF'
[commands]
upgrade_type = default
download_updates = yes
apply_updates = yes
random_sleep = 0

[emitters]
emit_via = stdio
EOF

  # Pick an available timer unit (varies by distro/version)
  timer_unit=""
  for candidate in dnf-automatic-install.timer dnf-automatic.timer; do
    if systemctl list-unit-files --type=timer | awk '{print $1}' | grep -qx "$candidate"; then
      timer_unit="$candidate"
      break
    fi
  done

  if [[ -z "$timer_unit" ]]; then
    echo "Installed dnf-automatic, but couldn't find a dnf-automatic*.timer unit to enable."
    exit 1
  fi

  # Override schedule to Sundays at 02:00 (clears any default OnCalendar)
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
