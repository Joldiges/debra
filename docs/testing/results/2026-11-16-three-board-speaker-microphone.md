---
title: Speaker and microphone check on all three lab boards
date: 2026-11-16
type: test-result
status: unreviewed
task: unauthored — James asked for the check in session
author: OpenCode session
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - "Pi 5 `debra-3c6b3f`, Pi Zero 2 W `debra-8518d6`, Pi Zero W `debra-f943dc`, measured 2026-11-16"
  - "tone: 1 kHz sine, −20 dBFS, 2.0 s, 48 kHz stereo"
  - "capture: parecord raw s16le 48 kHz 2ch from the PipeWire source; sink volume 65% during the test, restored afterwards"
---

# Speaker and microphone check on all three lab boards

## Summary

Playback is fine on all three: the **sink monitor** receives a clean 1 kHz tone on
every board. The acoustic path — speaker into the room, picked up by the board's
own microphone — differs sharply, and on the Zero 2 W it revealed a real fault:
**its microphone was switched off at the mixer**, not merely quiet.

## Method

Two captures per board, both while playing the same 2 s tone:

- **Monitor capture** (`<sink>.monitor`): proves the tone reaches the sink. Says
  nothing about whether a speaker moves air.
- **Microphone capture** (the board's own input): proves the acoustic path, and
  is the only check that would catch a dead speaker or a dead microphone.

Levels are the amplitude of the 1 kHz component (Hann-windowed FFT, normalised to
a full-scale sine) in a silent window and in the tone window. Broadband RMS is
reported too, but it cannot separate a quiet tone from a noisy room.

## Results

| Board | Monitor 1 kHz | Mic 1 kHz silent → tone | Acoustic attenuation | Ambient RMS | Reading |
| --- | --- | --- | --- | --- | --- |
| Pi 5 (`debra-3c6b3f`) | 3275 | 0.6 → **1388** | −7.5 dB | −37.2 dBFS | speaker and microphone both good |
| Zero W (`debra-f943dc`) | 3038 | 0.2 → **57** | −35.2 dB | −26.8 dBFS | both work; high noise floor |
| Zero 2 W (`debra-8518d6`) as found | 3275 | 0.0 → **11.7** | −49.0 dB | −89.0 dBFS | **microphone effectively dead** |
| Zero 2 W after routing fix | 3275 | 2.2 → **348** | −19.5 dB | −52.6 dBFS | both work |

## The Zero 2 W fault

The capture path was not routed. Its capture gain was already at maximum (WM8960
`Capture` 63 = +30 dB, on) and the speaker was at 91%, yet the room read
−89 dBFS: at that gain a working microphone cannot be that quiet. The inputs
themselves were switched off:

| Control | As found | Needed |
| --- | --- | --- |
| `Left Input Mixer Boost` | off | on |
| `Right Input Mixer Boost` | off | on |
| `Left/Right Boost Mixer LINPUT1/RINPUT1` | on | on |
| `Capture` | 63 (+30 dB) | 63 |

Switching the two input mixers on raised the room from −89 to −52.6 dBFS and the
tone from 11.7 to 348 — a +44 dB change, with no other control touched. The
change is **in place on the board now** and **will not survive a reboot**; making
it durable needs an alsa-state restore or WirePlumber rule, which was not done.

This also explains a fact already recorded about this board: its LVA log has
never shown a wake-word detection. A deaf input is consistent with that, and the
"no wake word yet" gap recorded in `AGENTS.md` should be re-measured now that
capture works rather than assumed to be an audio-path question.

## The Zero W's noise floor

The Zero W detects the tone clearly (57 above 0.2, a 31 dB band-limited rise) so
both directions work, but its ambient floor is −26.8 dBFS against the Pi 5's
−37.2 dBFS on the same card, overlay and kernel family. Its PGA was 16 dB versus
the Pi 5's 12 dB, which accounts for about 4 dB of the 10 dB difference. The rest
is undiagnosed: room noise, the out-of-tree `tlv320aic3x` module the armv6 kernel
lacks in-tree, or supply noise on the single-core board. Not attributed.

## Limits

- This measures the speaker→air→microphone path. It is not a calibrated sound
  level, and it cannot be compared across rooms.
- The tone is 2 s at 65% sink volume on an unmuted output. It was audible.
- The Zero 2 W change was made to a live device with LVA running; mixer state was
  otherwise left as found, and sink volume was restored by each script.
- No wake-word, TTS or music playback was verified by this test.
