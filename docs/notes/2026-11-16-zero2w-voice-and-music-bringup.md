---
title: Pi Zero 2 W voice and music bring-up, and two silent misconfigurations
date: 2026-11-16
type: project-learning
status: unreviewed
task: none
author: OpenCode coordinator session
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - Observed on debra-8518d6 (Pi Zero 2 W, WM8960 HAT) 2026-11-16
  - tools/device/lab-zero2w/README.md and scripts
  - docs/testing/results/2026-11-16-zero2w-web-portal-and-hat-audio.md
supersedes: []
---

## Summary

The board now runs PipeWire, Linux Voice Assistant (LVA v1.1.18) and Sendspin
9.1.0 as user services, all enabled and surviving a reboot, and Sendspin
reconnects to the household Music Assistant. Two failures were **silent**: the
codec was never connected to any output (healthy service, moving volume slider,
no sound and no error), and LVA advertised `0.0.0.0` over mDNS so Home
Assistant could never reach it. Both are fixed and recorded in the device build.

## Claims and evidence

| Kind | Claim | Source / date / hardware-version scope | Verification and limits |
| --- | --- | --- | --- |
| observed | The WM8960 overlay leaves `Left/Right Output Mixer PCM` off, so the card is silent with every service green. | debra-8518d6, 2026-11-16 | 1 kHz tone at 40% sink volume recorded from the HAT's own microphone: mixer off gave no 1 kHz energy (ratio 2.6 against a 1.5 kHz control), mixer on gave ratio 7812. |
| observed | This board's speaker is on the class-D output, not the headphone jack. | debra-8518d6, 2026-11-16 | Headphone volume 70/127 with the output mixer on produced no tone; adding `Speaker DC/AC` at 5 produced it. |
| observed | Setting `HOST=0.0.0.0` in the LVA unit makes it advertise `address = [0.0.0.0]` in `_esphomelib._tcp`, so Home Assistant cannot reach the satellite. | debra-8518d6, 2026-11-16 | `avahi-browse -rt _esphomelib._tcp` from another machine showed `address = [0.0.0.0]`; after removing `HOST`, the same command showed `192.168.0.99`. |
| observed | With gain fixed at capture PGA 63 (+30 dB) and ADC digital 195 (0 dB), room noise peaks about -42 dBFS; the input mixer boost stage clips on room noise alone. | debra-8518d6, 2026-11-16 | Eight combinations of boost switch and boost volume recorded and measured. |
| observed | LVA runs the wake-word engine at about 36% of one core; Sendspin is 0% idle and 32% during its first 40 s. | debra-8518d6, 2026-11-16 | `/proc/<pid>/stat` ticks over 10 s; RSS 22 MiB (LVA) and 108 MiB (Sendspin). |
| observed | Both services plus PipeWire and the web page fit in 246 of 415 MiB after a reboot. | debra-8518d6, 2026-11-16 | `free -m` after reboot with everything active: 169 MiB left, against LVA's stated 512 MiB minimum. |
| observed | Sendspin reconnects to the household Music Assistant after a reboot with no configuration. | debra-8518d6, 2026-11-16 | `sendspin.log`: `Admitted server 'Music Assistant (...)'`. |
| open-question | Whether the wake word triggers and a spoken reply plays on this HAT. | Not tested | Nobody spoke at the board during bring-up; the speaker path and the microphone path were measured separately, not as one pipeline. |
| open-question | Whether the class-D path is loud enough at ordinary listening volume, and whether the codec needs `MIC_AUTO_GAIN=1`. | Not tested with speech | The tone was measurable but quiet at 40% sink volume; gain is a starting point. |

## Verification

- Exact safe commands/procedure and working directory:
  - On the device, as `debra`: `tools/device/lab-zero2w/00-packages.sh`, then
    `10-audio.sh`, `11-mixer.sh`, `20-lva.sh`, `30-sendspin.sh`.
  - `systemctl --user is-active` for the six units; `ss -lntp` for 6053/8787/8928;
    `avahi-browse -rt _esphomelib._tcp` from another machine.
- Observed results: pass — six units active after `systemctl reboot`; LVA bound
  to `192.168.0.99:6053` and advertising that address; Sendspin on 8928 and
  connected to Music Assistant; mixer values restored by `alsa-restore`.
- Not tested, conflicting evidence, and remaining uncertainty: the wake word,
  speech-to-text, intent and reply were **not** run end to end on this board;
  Home Assistant has not been pointed at it by this session.
- Sanitized artifact references: `docs/testing/results/2026-11-16-zero2w-web-portal-and-hat-audio.md`
  for the earlier portal and HAT evidence.

## Handoff and correction links

- Current state and relevant base/candidate revision: `tools/device/lab-zero2w/`
  at the commit that added it; services enabled and running on `debra-8518d6`.
- Concrete next action and prerequisites: add the satellite in Home Assistant
  (ESPHome integration at `192.168.0.99:6053`, or accept the discovery card) and
  run one spoken wake word to reply. If recognition is poor, try
  `MIC_AUTO_GAIN=1` in the LVA unit before changing codec gain.
- Authorization needed; do not treat this suggestion as permission: none beyond
  the named board.
- Earlier claim superseded, if this is a correction: the earlier record said the
  codec's playback path was "not measured"; it is measured now, and the answer
  was that it was misconfigured.
- Reviewed report/decision that later adopts this finding, if known: none yet.
