#!/usr/bin/env python3
"""Check the stop-word gate on the device without playing any audio.

Feeds a "stop" clip straight into the feature frontend and drives
``linux_voice_assistant.stop_word.process_stop_word`` against the real stop
model, so it exercises the gating logic and the model reload without routing
sound to a speaker. It does not exercise the audio loop wiring in
``__main__.py``.

Run on the board, from the LVA checkout:

    .venv/bin/python ~/zero-w-workarounds/check-stop-word.py

Expected on the Pi Zero W with a 16 kHz mono "stop" recording:

    [inactive] active=False inferences=0 frames=78 stopped=no
    [active]   active=True  inferences=46 frames=46 stopped=yes at frame 46
    RESULT: PASS

``inferences=0`` while inactive is the whole point of the patch; ``stopped=yes``
while active is what proves the reset-on-reactivation path still detects.
"""

import sys
import types
import wave

from pymicro_wakeword import MicroWakeWord, MicroWakeWordFeatures

from linux_voice_assistant.stop_word import process_stop_word

WAKEWORDS = "/home/debra/linux-voice-assistant/wakewords"
CLIP = "/tmp/stop16.wav"
BLOCK = 1024
THRESHOLD = 0.5


def load_clip(path):
    """Read a 16 kHz mono 16-bit WAV and return raw PCM bytes."""
    with wave.open(path) as wav:
        if wav.getframerate() != 16000 or wav.getnchannels() != 1:
            raise SystemExit(f"{path} must be 16 kHz mono")
        return wav.readframes(wav.getnframes())


def run(label, active):
    """Run the clip with the stop word inactive or active. Returns (calls, frame)."""
    stop = MicroWakeWord.from_config(config_path=f"{WAKEWORDS}/stop.json")
    stop.id = "stop"
    state = types.SimpleNamespace(
        stop_word=stop,
        active_wake_words={"stop"} if active else set(),
        stop_word_threshold=THRESHOLD,
    )

    calls = [0]
    original = stop.process_streaming

    def counted(features):
        calls[0] += 1
        return original(features)

    stop.process_streaming = counted

    audio = load_clip(CLIP)
    frontend = MicroWakeWordFeatures()
    running = False
    frames = 0
    stopped_at = None

    for offset in range(0, len(audio) - BLOCK, BLOCK):
        micro_inputs = list(frontend.process_streaming(audio[offset : offset + BLOCK]))
        frames += len(micro_inputs)
        stopped, running = process_stop_word(state, micro_inputs, running)
        if stopped:
            stopped_at = frames
            break

    print(
        f"[{label}] active={active} inferences={calls[0]} "
        f"frames={frames} "
        f"stopped={'yes at frame %d' % stopped_at if stopped_at else 'no'}"
    )
    return calls[0], stopped_at


def main():
    inactive_calls, inactive_hit = run("inactive", active=False)
    active_calls, active_hit = run("active", active=True)

    failures = []
    if inactive_calls != 0:
        failures.append("the stop model ran while the stop word was inactive")
    if inactive_hit is not None:
        failures.append("the stop word acted while inactive")
    if active_calls == 0:
        failures.append("the stop model never ran while active")
    if active_hit is None:
        failures.append("the stop word was not detected while active")

    for failure in failures:
        print(f"FAIL: {failure}")

    print("RESULT:", "FAIL" if failures else "PASS")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
