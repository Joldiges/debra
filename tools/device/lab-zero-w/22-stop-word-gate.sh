#!/bin/sh
# Apply the stop-word gating patch to the pinned LVA checkout.
#
# The stop model is inferred on every audio frame although it can only act while
# a reply, announcement or timer is playing. On one ARM1176 core that was 41.9%
# of the core before and 30.9% after, measured 2026-11-16 (see the CPU
# accounting note in docs/notes/).
#
# The patch is idempotent: an already-patched checkout is reported and left
# alone, and a checkout that is neither clean nor patched is refused so a
# half-applied state cannot be mistaken for success.
#
# TODO(migrate): delete this script and the patch when a linux-voice-assistant
#   release contains the gate (OHF-Voice/linux-voice-assistant#526). Then the
#   only Zero W workarounds left are the ARMv6 library and the dependency pins.
#
# Usage: LVA_DIR=~/linux-voice-assistant ./22-stop-word-gate.sh
set -eu

DIR="${LVA_DIR:-$HOME/linux-voice-assistant}"
HERE=$(cd "$(dirname "$0")" && pwd)
PATCH="$HERE/patches/0001-gate-idle-stop-word-v1.1.18.patch"

cd "$DIR"

if git apply --reverse --check "$PATCH" 2>/dev/null; then
  echo "stop-word gate: already applied"
elif git apply --check "$PATCH" 2>/dev/null; then
  git apply "$PATCH"
  echo "stop-word gate: applied"
else
  echo "stop-word gate: the checkout is neither clean nor patched. Refusing." >&2
  echo "Reset with: git -C $DIR checkout -- linux_voice_assistant/__main__.py" >&2
  exit 1
fi

if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; else PYTHON=python3; fi
"$PYTHON" -m py_compile linux_voice_assistant/__main__.py
echo "stop-word gate: compiles cleanly"
