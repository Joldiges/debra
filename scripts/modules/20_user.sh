#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
NEW_USER="${2:?new user required}"
NEW_PASS="${3:?new password required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"

# Create new user if it doesn't exist
if id -u "${NEW_USER}" >/dev/null 2>&1; then
  echo "User ${NEW_USER} already exists"
else
    useradd -m -s /bin/bash "${NEW_USER}"
    # TODO: Some issue with password setting from the script...
    # echo "${NEW_USER}:${NEW_PASS}" | chpasswd || true
fi

# Enable linger for the new user to allow user services to run when not logged in
loginctl enable-linger "$NEW_USER"

# Add user to common groups
usermod -aG sudo,audio,video,dialout,plugdev,netdev,gpio,i2c,spi "${NEW_USER}" 2>/dev/null || true

# Copy SSH keys from source user if available
SRC_USER="${SUDO_USER:-}"
if [[ -n "${SRC_USER}" ]] && [[ -d "/home/${SRC_USER}/.ssh" ]]; then
  install -d -m 700 -o "${NEW_USER}" -g "${NEW_USER}" "/home/${NEW_USER}/.ssh"
  if [[ -f "/home/${SRC_USER}/.ssh/authorized_keys" ]]; then
    install -m 600 -o "${NEW_USER}" -g "${NEW_USER}" \
      "/home/${SRC_USER}/.ssh/authorized_keys" \
      "/home/${NEW_USER}/.ssh/authorized_keys"
  fi
fi

# # Lock default users
# if [[ "${LOCK_DEFAULT_USER:-0}" == "1" ]]; then
#   for u in pi ubuntu debian; do
#     if id -u "${u}" >/dev/null 2>&1 && [[ "${u}" != "${NEW_USER}" ]]; then
#       passwd -l "${u}" || true
#     fi
#   done
# fi
