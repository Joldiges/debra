#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
NEW_USER="${2:?new user required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"

export DEBIAN_FRONTEND=noninteractive

# -------- sanity --------
if [[ -z "${NEW_USER:-}" ]]; then
  echo "ERR: NEW_USER not set in config: ${NEW_USER}"
  exit 1
fi

if ! id "${NEW_USER}" &>/dev/null; then
  echo "ERR: NEW_USER '${NEW_USER}' does not exist yet"
  exit 1
fi

# -------- deps (root only) --------
apt-get update
apt-get install -y \
  git \
  python3 \
  python3-venv \
  python3-pip \
  build-essential \
  libportaudio2 \
  portaudio19-dev \
  libmpv-dev \
  mpv \
  avahi-daemon \
  pipewire \
  pipewire-pulse \
  wireplumber

# -------- paths --------
BASE="/opt/debra"
LVA_DIR="${BASE}/linux-voice-assistant"

install -d -m 755 "${BASE}"

# -------- clone --------
if [[ ! -d "${LVA_DIR}" ]]; then
  git clone https://github.com/OHF-Voice/linux-voice-assistant.git "${LVA_DIR}"
fi

chown -R "${NEW_USER}:${NEW_USER}" "${LVA_DIR}"

# -------- setup (as user) --------
cd "${LVA_DIR}"
git pull

if [[ ! -d ".venv" ]]; then
  sudo -u "${NEW_USER}" ./script/setup
fi

# -------- arguments --------
LVA_ARGS=(
  "--name" "${DEBRA_HOSTNAME}"
)

if [[ -n "${LVA_WAKE_MODEL:-}" ]]; then
  LVA_ARGS+=( "--wake-model" "${LVA_WAKE_MODEL}" )
fi

# -------- user systemd --------
USER_SYSTEMD_DIR="/home/${NEW_USER}/.config/systemd/user"
install -d -m 755 "${USER_SYSTEMD_DIR}"

cat >"${USER_SYSTEMD_DIR}/linux-voice-assistant.service" <<EOF
[Unit]
Description=Linux Voice Assistant (Debra)
Wants=pipewire.service pipewire-pulse.service
After=pipewire.service pipewire-pulse.service network-online.target

[Service]
WorkingDirectory=${LVA_DIR}
ExecStart=${LVA_DIR}/script/run ${LVA_ARGS[*]}
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
EOF

chown -R "${NEW_USER}:${NEW_USER}" "/home/${NEW_USER}/.config"

# -------- enable linger + service --------
loginctl enable-linger "$NEW_USER"
systemctl --machine="${NEW_USER}@.host" --user daemon-reload
systemctl --machine="${NEW_USER}@.host" --user enable pipewire pipewire-pulse wireplumber
systemctl --machine="${NEW_USER}@.host" --user enable --now linux-voice-assistant.service

echo "Linux Voice Assistant installed and running (user service)."
