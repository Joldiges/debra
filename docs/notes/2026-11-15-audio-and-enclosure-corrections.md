---
title: Corrections to audio-level, routing and speaker-replacement conclusions
date: 2026-11-15
type: project-learning
status: unreviewed
task: WEB01
author: OpenCode coordinator
author_model: openai/gpt-6.1-sol
author_variant: unknown
sources:
  - docs/testing/results/2026-11-15-lab-pi5-audio-levels.md
  - docs/design/audio-outputs.md
  - docs/notes/2026-11-15-james-fusion-model-quality-bar.md
  - James's enclosure, quiet-testing, browser and recovery steering, 2026-11-15 conversation
supersedes:
  - Incorrect volume arithmetic and safety/speech inferences in docs/testing/results/2026-11-15-lab-pi5-audio-levels.md
  - Unverified headphone routing, implemented-CLI and adopted-fan-out implications in docs/design/audio-outputs.md
  - Speaker replacement and fixed product-form conclusions in docs/notes/2026-11-15-james-fusion-model-quality-bar.md
---

# Correct the conclusions; preserve the observations

## Claims and evidence

| Kind | Correction | Evidence and limits |
| --- | --- | --- |
| observed arithmetic | The old table does **not** show +6 dB for doubling native percentage: 8→16% changes −77.5→−61.0 dBFS (+16.5 dB); 10→20% changes −72.7→−56.4 (+16.3 dB); 16→32% changes −61.0→−43.6 (+17.4 dB) | Recomputed from the published table, no new playback. A cubic-amplitude mapping predicts `60 log10(2) = 18.06 dB`, broadly consistent; this is not proof of every gain stage or absence of AGC |
| unsupported inference | A 1 kHz tone's captured dBFS does not measure speech level, comfort, acoustic safety, or next-room inaudibility | The old report measured one signal/path without dB SPL calibration. Its “16% quiet,” “26% safe,” inferred normal reply level, and tone-versus-speech bounds must not authorize sound |
| user-requirement | Investigations stay silent: no test tones or volume increases while the baby/household is asleep | James's 2026-11-15 steering; not replaced by a calculated supposedly safe level |
| unknown | LINE→amplifier→speaker is supported by the bring-up evidence; the exact 3.5 mm headphone tap remains unverified | Silence from the on-board microphone with nothing in the jack does not locate the jack electrically or prove headphone behavior. `HP DAC` was recorded at 0 (register value), not established as “0 dB” |
| correction | No `debra-audio outputs …` CLI exists; the former command block was a design sketch | No implementation in the repository. Browser volume uses an explicit native sink instead |
| proposed-decision | Announcement fan-out separate from a single selected music sink is an option, not an adopted default | Loading a combine/echo-cancel module does not prove sync quality, echo reduction, hotplug recovery or safe all-output levels. Temporary modules were removed in the prior session |
| user-requirement | Reconstruct James's original `RPiSpeaker_v17`, retaining his existing square speaker/four screws, forward speaker/microphones, desktop/wall use and accessible topper | Supersedes the earlier inference that the speaker must change. STEP bounding boxes/cylinder radii alone do not identify the complete speaker, acoustic opening or intended finished assembly |

## Verification and uncertainty

Read the published table and earlier claims; recalculated the three differences
above. No device access, audio, recordings or CAD modification for this note.
Do not retroactively relabel the original author's model or erase the old note.
The historical gain sweep remains evidence about that setup only.

Next: route browser volume through the explicit native sink; keep independent
output/duck/cancellation research source-pinned, and obtain physical fit-critical
speaker/HAT measurements before a production enclosure. None of those follow-ups
grants live-device or audible-test permission.
