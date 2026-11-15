#!/bin/sh
# Acoustic check: play a 1 kHz tone out of the HAT while recording from it.
# Reports capture levels in dBFS, so it shows both that audio reaches the
# speaker and that the capture path is alive and not clipping.
#
# Usage: 12-loopback.sh [sink-id] [source-id]
set -eu
SINK="${1:-}"
SOURCE="${2:-}"

ffmpeg -y -f lavfi -i "sine=frequency=1000:duration=4" -ar 48000 -ac 2 /tmp/tone.wav >/dev/null 2>&1

timeout 6 pw-record ${SOURCE:+--target "$SOURCE"} --channels 2 --rate 48000 /tmp/rec.wav &
sleep 1
pw-play ${SINK:+--target "$SINK"} /tmp/tone.wav
sleep 1
wait || true

echo "--- capture level while the tone plays ---"
ffmpeg -i /tmp/rec.wav -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume"
