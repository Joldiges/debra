#!/bin/sh
# Install the ARMv6 libtensorflowlite_c.so into both wake-word engines.
#
# The piwheels ARM wheels of pymicro-wakeword and pyopen-wakeword contain an
# x86-64 library, so the engines import but cannot load a model. This copies a
# pinned ARMv6 build over the bundled file in both packages and verifies the
# bytes and the ELF machine.
#
# TODO(migrate): retire this step when a pymicro-wakeword release ships
#   lib/linux_armv6l (OHF-Voice/pymicro-wakeword#22). pyopen-wakeword has no
#   equivalent fix, so that half needs its own upstream change or stays local.
#
# Usage: LVA_DIR=~/linux-voice-assistant ./21-armv6-tflite.sh
set -eu

DIR="${LVA_DIR:-$HOME/linux-voice-assistant}"
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/pins.env"

SITE=$(find "$DIR/.venv/lib" -maxdepth 2 -type d -name site-packages 2>/dev/null | head -1)
if [ -z "$SITE" ]; then
  echo "No virtualenv under $DIR/.venv; run 20-lva.sh first." >&2
  exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

git -C "$tmp" init -q
git -C "$tmp" fetch -q --depth 1 "$PW_REPO" "$PW_SHA"
git -C "$tmp" show "$PW_SHA:$PW_LIB_PATH" > "$tmp/libtensorflowlite_c.so"

actual=$(sha256sum "$tmp/libtensorflowlite_c.so" | cut -d' ' -f1)
if [ "$actual" != "$PW_LIB_SHA256" ]; then
  echo "Library hash mismatch: got $actual, expected $PW_LIB_SHA256" >&2
  exit 1
fi

machine=$(readelf -h "$tmp/libtensorflowlite_c.so" | awk '/Machine:/{print $2, $3}')
if [ "$machine" != "ARM " ] && [ "$machine" != "ARM" ]; then
  echo "Not an ARM binary (Machine: $machine)" >&2
  exit 1
fi

for package in pymicro_wakeword pyopen_wakeword; do
  dest="$SITE/$package/lib"
  if [ ! -d "$dest" ]; then
    echo "Missing $dest; is the package installed?" >&2
    exit 1
  fi
  install -m 0644 "$tmp/libtensorflowlite_c.so" "$dest/libtensorflowlite_c.so"
  echo "installed ARMv6 library into $package"
done

echo "libtensorflowlite_c.so: $PW_LIB_SHA256 (ARMv6) in both engines"
