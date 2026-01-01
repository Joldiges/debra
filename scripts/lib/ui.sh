#!/usr/bin/env bash
set -euo pipefail

prompt_string() {
  local label="$1"
  local default="${2:-}"
  local val=""
  if [[ -n "${default}" ]]; then
    read -r -p "${label} [${default}]: " val
    echo "${val:-${default}}"
  else
    read -r -p "${label}: " val
    echo "${val}"
  fi
}

prompt_secret() {
  local label="$1"
  local val1="" val2=""
  while true; do
    read -r -s -p "${label}: " val1; echo
    read -r -s -p "Confirm ${label}: " val2; echo
    [[ "${val1}" == "${val2}" ]] && [[ -n "${val1}" ]] && break
    echo "Passwords didn't match (or empty). Try again."
  done
  echo "${val1}"
}

prompt_yesno() {
  local label="$1"
  local default="${2:-no}" # yes/no
  local prompt="[y/N]"
  [[ "${default}" == "yes" ]] && prompt="[Y/n]"

  while true; do
    read -r -p "${label} ${prompt}: " ans
    ans="$(echo "${ans}" | tr '[:upper:]' '[:lower:]')"
    if [[ -z "${ans}" ]]; then
      [[ "${default}" == "yes" ]] && return 0 || return 1
    fi
    case "${ans}" in
      y|yes) return 0 ;;
      n|no)  return 1 ;;
      *) echo "Answer yes or no." ;;
    esac
  done
}
