#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"

if [[ "${ENABLE_SENDSPIN:-0}" != "1" ]]; then
  exit 0
fi

export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends python3-venv
# TODO: Refine this.  Issue building CFFI (missing Python.h).
apt-get install -y --no-install-recommends libffi-dev python3-dev pkg-config build-essential

VENV="/opt/debra/sendspin-venv"
mkdir -p /opt/debra
python3 -m venv "${VENV}"
"${VENV}/bin/pip" install --upgrade pip
"${VENV}/bin/pip" install --upgrade sendspin

SENDSPIN_ARGS="--headless --id sendspin-${DEBRA_HOSTNAME} --name ${DEBRA_HOSTNAME}"
if [[ -n "${SENDSPIN_URL:-}" ]]; then
  SENDSPIN_ARGS="${SENDSPIN_ARGS} --url ${SENDSPIN_URL}"
fi

cat >/etc/systemd/system/sendspin.service <<EOF
[Unit]
Description=Sendspin headless receiver
Wants=network-online.target avahi-daemon.service
After=network-online.target avahi-daemon.service

[Service]
Type=simple
ExecStart=${VENV}/bin/sendspin ${SENDSPIN_ARGS}
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now sendspin.service
