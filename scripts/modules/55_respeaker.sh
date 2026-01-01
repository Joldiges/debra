#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"

if [[ "${DEBRA_PLATFORM}" != "raspberrypi" ]]; then
  echo "Not a Raspberry Pi; skipping ReSpeaker setup."
  exit 0
fi

export DEBIAN_FRONTEND=noninteractive

say() { echo "==> $*"; }
prompt_string() {
  local label="$1"
  local val=""
  while [[ -z "$val" ]]; do
    read -r -p "$label: " val
    val="${val,,}"  # lowercase
  done
  echo "$val"
}

say "ReSpeaker driver setup."
say "If using ReSpeaker 2-Mic Pi HAT, pick version:"
echo "  - v1 (older PCB)"
echo "  - v2 (newer PCB)"
echo ""
echo "See hardware images at:"
echo " https://files.seeedstudio.com/wiki/ReSpeaker_2_Mics_Pi_HAT/v2/pcn.webp"
echo ""
RE_SPEAKER_VER=""

while true; do
  RE_SPEAKER_VER="$(prompt_string "Enter version (v1 or v2)" )"
  if [[ "${RE_SPEAKER_VER}" == "v1" ]] || [[ "${RE_SPEAKER_VER}" == "v2" ]]; then
    break
  fi
  echo "Please enter exactly 'v1' or 'v2'."
done

say "Selected ReSpeaker $RE_SPEAKER_VER"

KVER=$(uname -r | cut -d. -f1-2)
WORKDIR="/opt/debra/seeed-voicecard"

if [[ ! -d "${WORKDIR}" ]]; then
  mkdir -p /opt/debra
  git clone https://github.com/HinTak/seeed-voicecard.git "${WORKDIR}"
fi

cd "${WORKDIR}"
git fetch
git checkout "v$KVER"

CFG=/boot/firmware/config.txt
[ -f "$CFG" ] || CFG=/boot/config.txt

if [[ "$RE_SPEAKER_VER" == "v1" ]]; then
  say "Using ReSpeaker v1 installation instructions"
  # From: https://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT_Raspberry/
    #     CFG=/boot/firmware/config.txt
    #     [ -f "$CFG" ] || CFG=/boot/config.txt
    #
    #     grep -q '^dtoverlay=seeed-2mic-voicecard' "$CFG" \
    #       || echo 'dtoverlay=seeed-2mic-voicecard' >> "$CFG"
  ./install.sh
  # TODO: Second run since the first failed once... and I don't want to debug right now
  ./install.sh

  # Manually add the dtoverlay line since the script didn't seem to?

  grep -q '^dtoverlay=seeed-2mic-voicecard' "$CFG" || \
  printf '\n[all]\ndtoverlay=seeed-2mic-voicecard\n' >> "$CFG"

  # Lock kernel version
  K=$(uname -r)
  sudo apt-mark hold \
    linux-image-$K \
    linux-headers-$K \
    linux-headers-${K%%-*}-common-rpi 2>/dev/null || true
elif [[ "$RE_SPEAKER_VER" == "v2" ]]; then
  say "Using ReSpeaker v2 installation instructions"
  # v2 has alternate setup in upstream scripts
  # TODO: Differs from V1?
  # From (not really): https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/
  #     ./install.sh
  curl https://raw.githubusercontent.com/Seeed-Studio/seeed-linux-dtoverlays/refs/heads/master/overlays/rpi/respeaker-2mic-v2_0-overlay.dts -o respeaker-2mic-v2_0-overlay.dts
  dtc -I dts respeaker-2mic-v2_0-overlay.dts -o respeaker-2mic-v2_0-overlay.dtbo
  sudo dtoverlay respeaker-2mic-v2_0-overlay.dtbo
  sudo cp respeaker-2mic-v2_0-overlay.dtbo /boot/firmware/overlays

  # TODO: This can be made generic where the dtoverlay item is a variable
  grep -q '^dtoverlay=respeaker-2mic-v2_0-overlay' "$CFG" || \
  printf '\n[all]\ndtoverlay=respeaker-2mic-v2_0-overlay\n' >> "$CFG"
fi

say "ReSpeaker driver installed. Reboot required."
