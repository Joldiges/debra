#!/usr/bin/env bash
# 70-audio-level-probe.sh - find the lowest sink volume that still gives a usable
# microphone signal, without ever playing anything loud.
#
# Why: automated audio tests need the speaker to make a sound the microphones can
# hear, and this device lives in a house with people asleep in it. This sweeps a
# 1 kHz tone upward from a very low volume and stops as soon as the tone is
# clearly above the noise floor, then restores the volume it found on arrival.
#
# It plays at most TONE_SEC seconds per step and never goes above MAX_PCT.
#
# Two things this script learned the hard way, both recorded here because they
# will bite any future audio test:
#
#   * pw-play/pw-record must be used, not aplay/arecord. Only the PipeWire path
#     applies the sink volume; aplay talks to ALSA directly and would make every
#     step equally loud.
#   * pw-play -a (raw) does not read a regular file: it exits 0 after ~84 ms
#     having played nothing. Write a real WAV and let libsndfile read it.
#
# The level is measured in the tone's own frequency bin (Goertzel), not as
# broadband RMS. This codec's capture carries a DC offset around -37 dBFS and a
# low-frequency rumble that together swamp a broadband measurement.
#
# Usage: ./70-audio-level-probe.sh [max-percent]
# Env:   STOP_SNR (dB, default 25)  MAX_PCT (default 20)  TONE_HZ  TONE_SEC  REC_SEC
set -euo pipefail

MAX_PCT="${1:-${MAX_PCT:-20}}"
STOP_SNR="${STOP_SNR:-25}"
TONE_HZ="${TONE_HZ:-1000}"
TONE_SEC="${TONE_SEC:-1.0}"
REC_SEC="${REC_SEC:-3.0}"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

python3 - "$WORK" "$MAX_PCT" "$STOP_SNR" "$TONE_HZ" "$TONE_SEC" "$REC_SEC" <<'PY'
import math, os, struct, subprocess, sys, threading, time, wave

work, max_pct, stop_snr, tone_hz, tone_sec, rec_sec = sys.argv[1:7]
max_pct, stop_snr = float(max_pct), float(stop_snr)
tone_hz, tone_sec, rec_sec = float(tone_hz), float(tone_sec), float(rec_sec)
SR = 48000


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def sink_volume():
    out = run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"]).stdout
    # "Volume: front-left: 23593 /  36% / -26.62 dB,   front-right: ..."
    return out.split("/")[1].strip()


def set_sink_volume(pct):
    run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct:g}%"])


def make_tone(path):
    n = int(SR * tone_sec)
    frames = bytearray()
    for i in range(n):
        # 0.5 full scale: the sink volume, not the tone, is the attenuator
        s = int(0.5 * 32767 * math.sin(2 * math.pi * tone_hz * i / SR))
        frames += struct.pack("<hh", s, s)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))


def record_raw(seconds):
    """Capture exactly `seconds` of mono s16 from the default source."""
    want = int(SR * seconds) * 2
    p = subprocess.Popen(
        ["pw-record", "-a", "--rate", str(SR), "--channels", "1", "--format", "s16", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    buf = bytearray()
    try:
        while len(buf) < want:
            chunk = p.stdout.read(min(65536, want - len(buf)))
            if not chunk:
                break
            buf += chunk
    finally:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    return bytes(buf)


def window(data, start, end):
    """Samples in [start, end) seconds, with the DC offset removed."""
    n = len(data) // 2
    a, b = max(0, int(start * SR)), min(n, int(end * SR))
    vals = struct.unpack(f"<{b - a}h", data[a * 2:b * 2])
    if not vals:
        return []
    mean = sum(vals) / len(vals)
    return [v - mean for v in vals]


def goertzel(vals, freq, sr=SR):
    """Magnitude of one frequency bin; a full-scale sine reads 1.0."""
    n = len(vals)
    if not n:
        return 0.0
    k = int(0.5 + n * freq / sr)
    w = 2 * math.pi * k / n
    c = 2 * math.cos(w)
    s0 = s1 = s2 = 0.0
    for v in vals:
        s0 = v + c * s1 - s2
        s2, s1 = s1, s0
    power = s1 * s1 + s2 * s2 - c * s1 * s2
    return 2 * math.sqrt(max(power, 0.0)) / n / 32768.0


def best_bin(data, freq, win=0.25, step=0.0625):
    """Strongest reading of `freq` in any window, so a late stream start does not
    matter. PipeWire suspends an idle sink, and the first tenths of a second of
    playback can be lost; assuming the tone begins at a fixed offset reads
    several dB low, and non-monotonically."""
    n = len(data) // 2
    wlen = int(win * SR)
    hop = max(1, int(step * SR))
    best = 0.0
    for a in range(0, max(1, n - wlen), hop):
        vals = struct.unpack(f"<{wlen}h", data[a * 2:(a + wlen) * 2])
        mean = sum(vals) / len(vals)
        mag = goertzel([v - mean for v in vals], freq)
        if mag > best:
            best = mag
    return best


def dbfs(x):
    return 20 * math.log10(x) if x > 0 else -120.0


def rms(vals):
    return math.sqrt(sum(v * v for v in vals) / len(vals)) / 32768.0 if vals else 0.0


def play_and_record(seconds, tone):
    """Start recording, let the stream settle, play the tone, collect."""
    holder = {}

    def worker():
        holder["data"] = record_raw(seconds)

    t = threading.Thread(target=worker)
    t.start()
    time.sleep(0.6)
    subprocess.run(["pw-play", tone], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=tone_sec + 20)
    t.join(timeout=seconds + 20)
    return holder.get("data", b"")


tone = os.path.join(work, "tone.wav")
make_tone(tone)

before = sink_volume()
src = run(["pactl", "get-source-volume", "@DEFAULT_SOURCE@"]).stdout.strip()
print(f"sink volume on arrival: {before}")
print(f"source volume: {src.splitlines()[0] if src else 'unknown'}")
print()

# --- noise floor: same recording path, same analysis, nothing playing
set_sink_volume(0)
data = record_raw(rec_sec)
if not data:
    print("record failed: pw-record produced no audio")
    sys.exit(1)
floor_win = window(data, 0.3, rec_sec - 0.2)
floor_bin = best_bin(data, tone_hz)
print(f"noise floor, {tone_hz:g} Hz bin: {dbfs(floor_bin):7.1f} dBFS   "
      f"(broadband rms {dbfs(rms(floor_win)):6.1f} dBFS)")
print()
print(f"{'vol':>5}  {'tone bin':>9}  {'rms dBFS':>9}  {'SNR dB':>7}")
print(f"{'-'*5}  {'-'*9}  {'-'*9}  {'-'*7}")

steps = [2, 3, 4, 6, 8, 10, 13, 16, 20, 26, 32, 36, 45]
found = None
try:
    for pct in steps:
        if pct > max_pct:
            break
        set_sink_volume(pct)
        data = play_and_record(rec_sec, tone)
        win = window(data, 0.3, rec_sec - 0.2)
        level = best_bin(data, tone_hz)
        snr = dbfs(level) - dbfs(floor_bin)
        print(f"{pct:4d}%  {dbfs(level):9.1f}  {dbfs(rms(win)):9.1f}  {snr:7.1f}", flush=True)
        if snr >= stop_snr and found is None:
            found = pct
            break
finally:
    # Always put the volume back, even on Ctrl-C or an exception.
    set_sink_volume(0)
    time.sleep(0.2)
    set_sink_volume(float(before.rstrip("%")))

after = sink_volume()
print()
if found is None:
    print(f"no volume up to {max_pct:g}% reached {stop_snr:g} dB SNR")
else:
    print(f"lowest usable volume: {found}%  (>= {stop_snr:g} dB above the noise floor)")
print(f"sink volume restored: {after}")
PY
