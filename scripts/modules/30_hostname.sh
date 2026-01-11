#!/usr/bin/env bash
set -euo pipefail

# Source common library
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/common.sh
source "${SCRIPT_DIR}/../lib/common.sh"

DEBRA_HOSTNAME="$(get_debra_hostname)"

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
