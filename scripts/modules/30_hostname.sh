#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"

NEW_HOST="${DEBRA_HOSTNAME:?missing hostname}"

echo "${NEW_HOST}" > /etc/hostname

# TODO: Double check this is right.0
# Observe /etc/hosts for more details
# TODO: hostname seems to not include the underscore?  something is whack...
if grep -qE '^127\.0\.1\.1' /etc/hosts; then
  sed -i "s/^127\.0\.1\.1.*/127.0.1.1\t${NEW_HOST}/" /etc/hosts
else
  echo -e "127.0.1.1\t${NEW_HOST}" >> /etc/hosts
fi

hostnamectl set-hostname "${NEW_HOST}" || true
