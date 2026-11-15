#!/usr/bin/env python3
"""Bounded, non-interactive audio self-test for a Raspberry Pi audio HAT.

Measures a stream, not a sound: microphone noise floor, microphone response to
a known tone played through the speaker, and clipping. Mixer state is saved
before any change and restored afterwards. Stdlib only (no numpy).
"""
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import time
import wave

CARD = sys.argv[1] if len(sys.argv) > 1 else "seeed2micvoicec"
DEV = "plughw:CARD=%s,DEV=0" % CARD
RATE = 48000
CH = 2
TONE_F = 1000.0
TONE_DBFS = -20.0
WORK = os.path.expanduser("~/debra-test")
STATE = "/tmp/debra-selftest-pre.state"
# /usr/sbin is not on the PATH of a non-login SSH session on Raspberry Pi OS.
ALSACTL = shutil.which("alsactl") or "/usr/sbin/alsactl"


def run(cmd, timeout=30):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def amixer(*args):
    return run(["amixer", "-c", CARD] + list(args))


def card_index():
    with open("/proc/asound/cards") as f:
        for line in f:
            if CARD in line:
                return int(line.split()[0])
    return None


def read_wav(path):
    with wave.open(path) as w:
        frames, ch, rate = w.getnframes(), w.getnchannels(), w.getframerate()
        raw = w.readframes(frames)
    s = struct.unpack("<%dh" % (len(raw) // 2), raw)
    return {"frames": frames, "channels": ch, "rate": rate,
            "left": list(s[0::2]), "right": list(s[1::2])}


def dbfs(v):
    return 20 * math.log10(v / 32768.0) if v > 0 else float("-inf")


def metrics(x):
    if not x:
        return {"rms": 0, "rms_dbfs": None, "peak": 0, "peak_dbfs": None, "clip_run": 0}
    rms = math.sqrt(sum(v * v for v in x) / len(x))
    peak = max(abs(v) for v in x)
    run_len = worst = 0
    for v in x:
        if abs(v) >= 32760:
            run_len += 1
            worst = max(worst, run_len)
        else:
            run_len = 0
    return {"rms": round(rms, 1), "rms_dbfs": round(dbfs(rms), 1),
            "peak": peak, "peak_dbfs": round(dbfs(peak), 1), "clip_run": worst}


def goertzel(x, freq, rate):
    n = len(x)
    k = int(0.5 + n * freq / rate)
    om = 2 * math.pi * k / n
    c = 2 * math.cos(om)
    s1 = s2 = 0.0
    for v in x:
        s0 = v + c * s1 - s2
        s2 = s1
        s1 = s0
    return s1 * s1 + s2 * s2 - c * s1 * s2


def tone_amplitude(x, freq=TONE_F):
    """Amplitude (in LSB) of a bin-centred sinusoid, by Goertzel."""
    return math.sqrt(max(goertzel(x, freq, RATE), 0.0)) / (len(x) / 2.0) if x else 0.0


def segment(x, t0, t1):
    return x[int(t0 * RATE):int(t1 * RATE)]


def write_tone(path, seconds=3.0):
    amp = int(32768 * 10 ** (TONE_DBFS / 20.0))
    frames = bytearray()
    for i in range(int(RATE * seconds)):
        v = int(amp * math.sin(2 * math.pi * TONE_F * i / RATE))
        frames += struct.pack("<hh", v, v)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))


def record(path, seconds):
    return run(["arecord", "-D", DEV, "-f", "S16_LE", "-r", str(RATE),
                "-c", str(CH), "-d", str(seconds), "-t", "wav", path],
               timeout=seconds + 30)


def main():
    os.makedirs(WORK, exist_ok=True)
    os.chdir(WORK)
    result = {"card": CARD, "card_index": card_index(), "device": DEV,
              "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "kernel": os.uname().release, "machine": os.uname().machine,
              "steps": {}, "verdict": {}}
    if result["card_index"] is None:
        result["verdict"]["card_present"] = False
        print(json.dumps(result, indent=2))
        return 1
    result["verdict"]["card_present"] = True

    idx = str(result["card_index"])
    st = run([ALSACTL, "-f", STATE, "store", idx])
    result["steps"]["mixer_store"] = {"rc": st.returncode, "file": STATE,
                                      "stderr": st.stderr.strip()}
    before = run(["amixer", "-c", idx, "scontents"]).stdout

    # Bounded, explicit mixer settings: expose why each is needed.
    applied = []
    for ctl, val in (("PGA", "24"), ("AGC", "off"), ("PCM", "127"),
                     ("HP DAC", "118"), ("HP", "5"),
                     ("Left HP Mixer DACL1", "on"), ("Right HP Mixer DACR1", "on")):
        r = amixer("sset", ctl, val)
        applied.append({"control": ctl, "value": val, "rc": r.returncode})
    result["steps"]["mixer_applied"] = applied
    result["steps"]["mixer_before"] = before

    write_tone(os.path.join(WORK, "tone1k.wav"))

    silence = os.path.join(WORK, "silence.wav")
    r = record(silence, 3)
    result["steps"]["silence_capture"] = {"rc": r.returncode, "stderr": r.stderr.strip()}
    sil = read_wav(silence)
    result["steps"]["silence_metrics"] = {"left": metrics(sil["left"]),
                                          "right": metrics(sil["right"]),
                                          "frames": sil["frames"]}

    loop = os.path.join(WORK, "loop.wav")
    proc = subprocess.Popen(["arecord", "-D", DEV, "-f", "S16_LE", "-r", str(RATE),
                             "-c", str(CH), "-d", "5", "-t", "wav", loop],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(1.0)
    play = run(["aplay", "-D", DEV, os.path.join(WORK, "tone1k.wav")], timeout=20)
    _, err = proc.communicate(timeout=30)
    result["steps"]["playback"] = {"rc": play.returncode, "stdout": play.stdout.strip(),
                                   "stderr": play.stderr.strip(), "capture_stderr": err.strip()}
    lp = read_wav(loop)
    pre_l = segment(lp["left"], 0.0, 0.9)
    pre_r = segment(lp["right"], 0.0, 0.9)
    tone_l = segment(lp["left"], 1.2, 3.8)
    tone_r = segment(lp["right"], 1.2, 3.8)
    post_l = segment(lp["left"], 4.2, 4.9)
    result["steps"]["loop_metrics"] = {
        "pre_tone_left": metrics(pre_l), "pre_tone_right": metrics(pre_r),
        "during_tone_left": metrics(tone_l), "during_tone_right": metrics(tone_r),
        "after_tone_left": metrics(post_l),
        "tone_amplitude_dbfs_left": round(dbfs(tone_amplitude(tone_l)), 1),
        "tone_amplitude_dbfs_right": round(dbfs(tone_amplitude(tone_r)), 1),
        "pre_tone_amplitude_dbfs_left": round(dbfs(tone_amplitude(pre_l)), 1),
        "after_tone_amplitude_dbfs_left": round(dbfs(tone_amplitude(post_l)), 1),
    }

    rst = run([ALSACTL, "-f", STATE, "restore", idx])
    result["steps"]["mixer_restore"] = {"rc": rst.returncode, "stderr": rst.stderr.strip()}
    result["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    m = result["steps"]["loop_metrics"]
    sig = m["tone_amplitude_dbfs_left"]
    floor = m["pre_tone_amplitude_dbfs_left"]
    result["verdict"].update({
        "capture_not_dead": result["steps"]["silence_metrics"]["left"]["rms"] > 0,
        "silence_clean": (result["steps"]["silence_metrics"]["left"]["clip_run"] == 0
                          and result["steps"]["silence_metrics"]["right"]["clip_run"] == 0),
        "tone_detected_in_mics": isinstance(sig, float) and isinstance(floor, float)
                                 and (sig - floor) >= 20.0,
        "tone_level_dbfs_left": sig,
        "pre_tone_level_dbfs_left": floor,
    })
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
