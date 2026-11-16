---
title: Pi Zero W CPU accounting for LVA, and which savings actually exist
date: 2026-11-16
type: project-learning
status: unreviewed
task: unauthored — investigation directed by James in session
author: OpenCode session
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - Pi Zero W Rev 1.1 at 192.168.0.70, Raspbian 13 (trixie), kernel 6.18.50+rpt-rpi-v6, CPython 3.13.5, observed 2026-11-16
  - OHF-Voice/linux-voice-assistant v1.1.18 (b55d36a), installed checkout on the device
  - pymicro-wakeword 2.5.0, pymicro-features 2.0.2, ARMv6 TFLite C 2.17.1 as installed
  - Benchmarks run read-only on the device; scripts in /tmp (not in Git): bench_lva.py, skip_sweep.py, block_sweep.py, diag.py
  - Patch applied to the device checkout 2026-11-16 11:34 and measured 11:24-11:43; branch fix/gate-idle-stop-word on Joldiges/linux-voice-assistant
  - https://www.home-assistant.io/voice_control/about_wake_word/ (accessed 2026-11-16)
  - https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/v1.1.18/docs/install_application.md (accessed 2026-11-16)
supersedes: []
---

# Pi Zero W CPU accounting for LVA

## Summary

The single ARM1176 core is dominated by LVA's on-device wake-word inference, not by
Python. The **stop-word model is inferred on every 10 ms frame although it can only
act while a reply, announcement or timer is playing** — roughly 38% of the audio
pipeline. Gating it on the signal the detection already uses measured
**41.9% → 30.9% of one core, −11.0 points absolute and −26% relative**, with the wake
word and the "stop" action both still working end to end. That is the only large
saving found. A Python upgrade is not a lever. Reducing the inference rate by
subsampling the feature stream does **not** work: the model carries state between
invokes and needs every consecutive window.

The patch is applied to the lab device and raised as a pull request against James's
LVA fork, not against upstream. Repository changes are this note, its index row, and
the V05 card with the roadmap/chain/progress wiring it needs.

## Claims and evidence

| Kind | Claim | Source / scope | Verification and limits |
| --- | --- | --- | --- |
| observed | The board is at capacity but not pinned: LVA ~40–50% of the one core, PipeWire stack ~10–13%, web dashboard ~3%, load average 2.5, `vmstat` `us` 47–92% / `id` 0–50% / `wa` 0 | Pi Zero W, 2026-11-16, `top`, `vmstat`, `uptime` | I/O wait is ~0, so this is CPU work, not a slow card |
| observed | Wake pipeline shares, over 10 s of audio: MicroFrontend 8%, `okay_nabu` 34%, `stop` 26%, total 69% of realtime | `/tmp/bench_lva.py`, run while the service was running | **Contended** with the live service, so absolute figures are inflated; the ratios are the usable part |
| observed | The stop model is invoked on every frame unconditionally: `__main__.py:886-892` loops `state.stop_word.process_streaming(micro_input)` with no condition | LVA v1.1.18 checkout | Read from source |
| observed | The stop word is added to `active_wake_words` only while TTS, an announcement or a timer is playing (`satellite.py:695,725,1025`) and removed when it ends (`998,1035,1109`), so the detection gate at `__main__.py:892` is false when idle | LVA v1.1.18 checkout | Read from source |
| observed | On the device the stop model fired 20 times and the stop action fired **0** times | `~/lab/lva.log` | Consistent with the gate: inference is spent, result discarded |
| observed | Skipping feature frames for the *next* inference destroys detection. Feeding every 2nd frame: 0/30 detections, median max-probability 0.013 (baseline 29/30, 0.985) | `/tmp/skip_sweep.py`, 30 espeak-ng "okay nabu" clips + 4 negatives | Non-consecutive frames; see the next row for the fairer variant, which also fails |
| observed | Keeping consecutive 3-frame windows but dropping whole windows also destroys detection: keep 1 of 2 → 0/30 (median 0.015); keep 1 of 3 → 0/30 (median 0.000); CPU falls 43%→25%→19% RT | `/tmp/block_sweep.py` | Sampling rate is not a free lever |
| observed | The model is **stateful across invokes**: the identical 3-feature input scores 0.68 with its normal history and 0.0 when earlier windows were dropped; raw maxima are 0.992 (every window), 0.242 (1 of 2), 0.000 (1 of 3) | `/tmp/diag.py` | Corroborated by `MicroWakeWord.reset()`, whose docstring is "Need to reload model to reset intermediary results" — the only way to clear state is to reload |
| upstream-documented | Home Assistant's default wake-word architecture is the reverse: the satellite streams audio and **HA** runs openWakeWord; on-device microWakeWord is the exception for ESP32/Android | HA `about_wake_word`, accessed 2026-11-16 | LVA speaks the ESPHome API, where the device starts the pipeline and audio flows only after a wake trigger. HA-side wake therefore needs a Wyoming satellite, not LVA |
| upstream-documented | Upstream added 32-bit **armv7** (not armv6) container builds on 2026-11-16 | LVA PR #344 / commit `25ec3f6` | ARM1176 cannot run an armv7 binary |
| observed | PyPy has no armv6/armhf build, and python-build-standalone publishes `armv7`, not `armv6` | PyPI/build listings inspected 2026-11-16 | A Python replacement is not available for this target |
| hypothesis → observed | Gating the stop model on `active_wake_words` cuts idle LVA CPU by about a quarter, relatively | `/tmp/measure_lva.sh` on the device, 480 s each side, 2026-11-16 | Confirmed relatively (−26%); the absolute expectation was wrong, see the next row |
| observed | LVA mean CPU fell from **41.9% to 30.9% of one core** (480 s idle each side), with a second 300 s sample at 32.8%: a 9–11 point saving, −26% relative | `BASELINE 480` at 11:24, `AFTER-PATCH 480` at 11:35, `AFTER-CONFIRM 300` at 11:50, device time | Same device and services, own `/proc/<pid>/stat`. The earlier "~26 points" estimate came from the 26%-of-realtime bench, which was contended and over-reads its shares |
| observed | After moving the gate into the PR's `stop_word.py` module, the board still measures **31.1% of one core** over 480 s idle | `AFTER-HELPER 480` at 13:10, device time, `/tmp/measure_lva.sh` | Same method and services as the row above; the refactor did not change the saving |
| observed | The shipped `stop_word.py` never invokes the model while the stop word is inactive, and detects the clip when active: 0 inferences / not stopped while inactive, 46 inferences / stopped at frame 46 of 78 while active | `/tmp/check_stop_word.py` in the device venv, real `stop` model and feature frontend, 2026-11-16 | Silent check, no speaker; it exercises the module, not the audio loop wiring |
| observed | `MicroWakeWord.reset()` costs 17–25 ms: it clears the feature and probability windows and reloads the TFLite model | Timed three times in the device venv | Small next to the sliding-window warm-up, so re-enabling the gate is cheap |
| observed | Reset then feed the "stop" clip: detected at feature frame 44 of 78, 113–132 ms wall | Harness in the device venv, 2026-11-16 | The re-enable path detects; the added audio delay is the ~150 ms window fill plus ~20 ms reload |
| observed | With the patch the wake word still detects and completes a cycle: probability 0.913, Home Assistant returned a TTS reply | `~/lab/lva.log`, 2026-11-16 11:46:16 | `~/sweep/s4_en-us+m3_180.wav` played through the HAT speaker into the real microphone path |
| observed | With the patch the stop word still interrupts a reply: probability 0.697 above the 0.5 threshold, `MpvMediaPlayer:stop()`, "TTS response stopped manually" | `~/lab/lva.log`, 2026-11-16 11:48:56 | espeak-ng "stop" at 16 kHz played 2.4 s into a TTS reply |
| open-question | Whether the ~4% of core PipeWire spends resampling 48 kHz→16 kHz is worth removing | `pw-top`: LVA client busy 2.7 ms per 64 ms period; graph rate 48000, capture 16000 | Setting the graph to 16 kHz would damage music playback on this board. Not proposed |
| open-question | 201 MB of 681 MB swap in use (zram + swapfile), `si`/`so` ~0 | `free -m`, `vmstat` | Not thrashing now; zram compression is still CPU on this class of board. Worth watching, not a finding |

## Verification

Run on the device from `~/linux-voice-assistant` with `.venv/bin/python`:

- `bench_lva.py` — 10 s of synthetic audio through the real `MicroWakeWordFeatures`
  and both models, timed per stage.
- `skip_sweep.py` — every Nth *feature frame* to the model, 30 positives + 4
  negatives, plus a 46 s concatenation for a stable CPU figure.
- `block_sweep.py` — same, but keeps whole consecutive windows and drops windows.
- `diag.py` — raw per-invoke probabilities, to separate "harness wrong" from
  "model genuinely fails".

Test audio was the 2026-11-16 bring-up sweep in `~/sweep/`: 30 espeak-ng variants of
"okay nabu" (voices m2–m5, 160–190 wpm, pitch ±20) and four negatives (`alexa`,
`hey jarvis`, `hey mycroft`, a non-wake clip). **Synthetic speech only**; this is a
bounded experiment, not a wake-word accuracy evaluation. It is strong enough to
reject "subsample the features" as an optimisation, because the failure is
categorical (0/30) rather than marginal.

For the applied patch the device-side sequence was:

- `python3 /tmp/apply_lva_patch.py` — refuses unless both anchors occur exactly once;
  printed the one-file diff, then `python -m py_compile` passed.
- `systemctl --user restart linux-voice-assistant` — reconnected to Home Assistant
  with no error in `~/lab/lva.log`.
- `/tmp/measure_lva.sh BASELINE 480`, then patch + restart, then
  `/tmp/measure_lva.sh AFTER-PATCH 480` (and a shorter confirmation run).
- `pw-play ~/sweep/s4_en-us+m3_180.wav` — wake detected; Home Assistant replied.
- `pw-play ~/sweep/stop16.wav` (espeak-ng "stop", 16 kHz mono, made on the host with
  `ffmpeg`) during the reply — stop detected and playback halted.

Not tested: a human voice, a second board, or the patched service under sustained
music playback. The `stop` percentages in the original accounting come from a
contended run; the 41.9→30.9 figure is a clean idle sample.

## Applied patch

The patch now adds `linux_voice_assistant/stop_word.py` **byte-identical to the one
in the pull request** (`sha256 8a587d8f…`) and rewires only the v1.1.18 call site,
so the board runs the same gating logic that is under review. The full diff, with
hash-verified pinning, is
[`tools/device/lab-zero-w/patches/0001-gate-idle-stop-word-v1.1.18.patch`](../../tools/device/lab-zero-w/patches/0001-gate-idle-stop-word-v1.1.18.patch).

The first form of the patch had the gate inline in `__main__.py` (26 insertions,
12 deletions) and is what produced the original measurement. It was replaced
because an inline version cannot be unit-tested: `process_audio()` is an
untested `while True` loop over a microphone, and `__main__` cannot even be
imported in a test without opening a PulseAudio context. The extracted helper
carries nine unit tests in the fork.

On the board, re-measured after the change with the same method
(`/tmp/measure_lva.sh`, 480 s idle): **31.1% of one core**, consistent with the
30.9% and 32.8% samples for the inline form. So the refactor kept the saving.

A silent check drove the shipped module with the real `stop` model and the
feature frontend, no speaker involved (`/tmp/check_stop_word.py`, 78 frames of a
synthetic "stop" clip):

| Case | Inferences | Result |
| --- | --- | --- |
| stop word inactive | 0 | not stopped, model never invoked |
| stop word active | 46 | stopped at frame 46 of 78 |

Measured cost: the model reload is 17–25 ms and the sliding window needs about
150 ms of audio, so a stop word spoken in the first ~170 ms of a reply can be
missed. Detection then works normally: the stop clip scored 0.697 and halted a
TTS reply on the device, and the wake word still completed a Home Assistant
round trip.

A Debra-side **setting** ("stop word: off / on", default off on Pi Zero W v1/v1.1)
is a separate change. It is not a one-liner: the web server has exactly two write
routes (`/api/audio/volume`, `/api/audio/mute`), `/api/setup` deliberately has no
POST path, and the page's design rule is that a capability which does not exist is
text, not a disabled control. A real toggle means a new authenticated POST route, a
persisted preference, a control with tests, per-board defaulting, and the LVA patch
above (LVA has no "disable stop word" flag — pointing `STOP_MODEL` at a missing name
trips `assert stop_model is not None`). That is a card, not a patch: it is prepared as
[V05](../work/cards/V05.md) in the `voice` chain, blocked on V02/C01.

## Before/after measurement (run)

Same device, same idle conditions, 480 s each side, all services left running and
LVA measured on its own `/proc/<pid>/stat`:

```sh
pid=$(pgrep -f 'linux_voice_assistant' | head -1)
hz=$(getconf CLK_TCK)
set -- $(awk '{print $14, $15}' /proc/$pid/stat); u1=$1; s1=$2
t1=$(cut -d' ' -f1 /proc/uptime)
sleep 480
set -- $(awk '{print $14, $15}' /proc/$pid/stat); u2=$1; s2=$2
t2=$(cut -d' ' -f1 /proc/uptime)
awk -v a=$u1 -v b=$s1 -v c=$u2 -v d=$s2 -v h=$hz -v x=$t1 -v y=$t2 \
  'BEGIN{printf "mean %.1f%% of one core over %.0fs\n", ((c+d)-(a+b))/h/(y-x)*100, y-x}'
```

Result: `BASELINE 41.9%` → `AFTER-PATCH 30.9%`, with a second 300 s sample after the
functional tests at `32.8%`. The patched steady state is therefore **31–33%**, a
9–11 point saving.

Pass criteria as originally written, all three: (1) mean LVA CPU falls by at least
15 percentage points — **not met on the absolute wording** (it fell 11.0 points,
−26% relative; the 15-point target came from the contended bench and was an
over-estimate); (2) the wake word still fires on `~/sweep/s4_en-us+m3_180.wav` —
**met**; (3) "stop" still interrupts a TTS reply or announcement — **met**. Revert
with `git -C ~/linux-voice-assistant checkout -- linux_voice_assistant/__main__.py`
and restart the user service.

## Upstream communication — pull request to James's fork, not upstream

James's instruction (2026-11-16) was to keep this off the upstream repository and
raise a branch and a local pull request on his own fork instead. Branch
`fix/gate-idle-stop-word` in `Joldiges/linux-voice-assistant`, opening against that
fork's `main`, at `25ec3f6`.

Title: Gate idle stop-word inference behind active_wake_words

Body: `process_audio()` loops `state.stop_word.process_streaming(micro_input)` for
every feature frame. The result is only used when `state.stop_word.id in
state.active_wake_words`, and that set contains the stop word only while a reply,
announcement or timer is playing (`satellite.py` adds it in `play_tts`,
`handle_message` and the timer branch, and removes it in `stop`, `_tts_finished`
and the timer auto-stop). When idle the inference is therefore computed and
discarded.

Measured on a Pi Zero W (LVA 1.1.18, pymicro-wakeword 2.5.0, ARMv6): the stop model
is ~26% of realtime in a contended bench and ~38% of the audio pipeline's CPU; over
a 10-hour run the log shows 20 stop-word activations and 0 stop actions. Gating the
loop on `active_wake_words`, and calling `stop_word.reset()` when it becomes
reachable again (the model keeps state between invokes), took idle LVA from 41.9% to
30.9% of the single core with the wake word and the stop action both still working.
The same change on a board with spare CPU costs one model reset per reply start.

Related observation, probably worth a second sentence rather than a second issue:
the model is stateful across invokes, so it cannot be run at a lower inference rate
by subsampling features. Anyone tempted to "just skip frames" should know it does
not work.

Suggested labels: performance, and the bug label only if maintainers agree the
idle inference is unintended.

## Also checked, not a saving

`--output-only` only changes which `supported_features` are advertised
(`satellite.py:89-96`); the wake and stop models still load and run, so it saves no
CPU. Established by reading the code, not by running the flag.

## Handoff and correction links

- Base: LVA `v1.1.18` (`b55d36a`) on the Pi Zero W; this repository's `main` at the
  time of writing.
- Applied: the patch is live on the lab device. Revert is one `git checkout` of
  `linux_voice_assistant/__main__.py` plus a service restart; a copy of the original
  file is at `/tmp/__main__.py.orig` on the device (temporary, not a backup).
- Raised: branch `fix/gate-idle-stop-word` and a pull request on
  `Joldiges/linux-voice-assistant`, not upstream.
- Next action: reviewed confirmation (a second idle sample and, ideally, a human
  voice), then decide whether Debra carries this as a scoped patch or waits for an
  upstream release; then implement V05's setting.
- Local workarounds are scripted in
  [`tools/device/lab-zero-w/`](../../tools/device/lab-zero-w/README.md): a pinned
  ARMv6 TFLite library and this patch, both hash-checked, with the upstream PRs
  that retire them recorded there.
- Authorization: task dispatch is **closed** (`python tools/taskchain.py list`);
  V05 is a prepared card and is `blocked` on V02/C01, so it is not claimable. The
  Debra-side setting needs that card and the wider config/architecture packets.
- Nothing here is reviewed evidence yet. The author is the same model that designed
  the experiment, so the before/after should be re-run by a reviewer.
