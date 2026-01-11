#!/usr/bin/env bash
set -euo pipefail

# Source common libraries
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"
# shellcheck source=../lib/ui.sh
source "${SCRIPT_DIR}/../lib/ui.sh"

# Get unique ID and hostname
DEBRA_HOSTNAME="$(get_debra_hostname)"

# Prompt for voice assistant settings
echo ""
echo "Voice satellite (Linux Voice Assistant) configuration"
LVA_WAKE_MODEL="$(prompt_string 'Wake model id' 'okay_nabu')"
LVA_AUDIO_INPUT="$(prompt_string 'Audio INPUT device (blank = auto/default)' '')"
LVA_AUDIO_OUTPUT="$(prompt_string 'Audio OUTPUT device (blank = auto/default)' '')"

NEW_USER=${SUDO_USER:-$(id -un)}


export DEBIAN_FRONTEND=noninteractive
## TODO: Only for Raspi 0 V1.  Edit - we shouldn't be building for this.  Handle missing wheels by building them in docker on a performant machine.
#export SKIP_CYTHON=1


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
sudo -u "${NEW_USER}" git -C "${LVA_DIR}" pull --ff-only

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

if [[ -n "${LVA_AUDIO_INPUT:-}" ]]; then
  LVA_ARGS+=( "--input-device" "${LVA_AUDIO_INPUT}" )
fi

if [[ -n "${LVA_AUDIO_OUTPUT:-}" ]]; then
  LVA_ARGS+=( "--output-device" "${LVA_AUDIO_OUTPUT}" )
fi

LVA_EXEC_ARGS="${LVA_ARGS[*]}"

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
ExecStart=${LVA_DIR}/script/run ${LVA_EXEC_ARGS}
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
