#!/usr/bin/env bash
set -euo pipefail

CFG_FILE="${1:?config file required}"
# shellcheck disable=SC1090
source "${CFG_FILE}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEBRA_ID="$("${SCRIPT_DIR}/../python/get_unique_id.py" --short 6)"
DEBRA_HOSTNAME="debra-${DEBRA_ID}"

echo "${DEBRA_HOSTNAME}" > /etc/hostname

# TODO: Double check this is right.0
# Observe /etc/hosts for more details
# TODO: hostname seems to not include the underscore?  something is whack...
if grep -qE '^127\.0\.1\.1' /etc/hosts; then
  sed -i "s/^127\.0\.1\.1.*/127.0.1.1\t${DEBRA_HOSTNAME}/" /etc/hosts
else
  echo -e "127.0.1.1\t${DEBRA_HOSTNAME}" >> /etc/hosts
fi

hostnamectl set-hostname "${DEBRA_HOSTNAME}" || true
