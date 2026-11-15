---
title: The v17 lid clears the reconstructed body, and the check is proven sensitive
date: 2026-11-15
type: project-learning
status: unreviewed
task: none (unblocked CAD check on the v17 front assembly)
author: OpenCode coordinator
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown (host reported no variant)
sources:
  - models/assemblies/rpispeaker-v17-body-lid/README.md (new report and reproduce commands)
  - models/parts/rpispeaker-v17-body/rpispeaker-v17-body.sc (base design, composed)
  - models/parts/rpispeaker-v17-lid/build-script.json (replayed on top of the body)
  - solidcraft-cli 0.42.0, headless, 2026-11-15
supersedes: []
---

## Summary

The [provisional v17 lid](../../models/parts/rpispeaker-v17-lid/README.md) and
the [reconstructed v17 body](../../models/parts/rpispeaker-v17-body/README.md)
**do not interfere**: 0 overlapping pairs, 2 bodies checked, 1 pair
Boolean-intersected, nothing unchecked, not truncated, at the lid's default
parameters. The lid's plate is not inside body material anywhere; it sits
0.30 mm from the bay wall at X 17.15 and its front face is flush with the body's
Y 15.50 plane. The sleeve's 0.45 mm reach over the Pi-side divider is an
adjacency at that plane rather than an overlap.

A deliberate control — `LD_CLEAR` changed from 0.3 to −0.2, making the plate
0.5 mm oversize per side — **is detected**: one pair, 5.5004 mm³, at
X 16.95–17.15, Y 13.90–15.50. A zero from a check that cannot fail is not
evidence; this one can.

The full report, renders and reproduce commands are in the
[assembly README](../../models/assemblies/rpispeaker-v17-body-lid/README.md).
This note records the result and the two composition details that took a failed
run to find.

## Claims and evidence

| Kind | Claim | Source / date / scope | Verification and limits |
| --- | --- | --- | --- |
| observed | Body and lid compose into one design without changing either body: Body 15,915.3915 mm³, Lid 4,028.8431 mm³, both closed | `solidcraft-cli eval` on the composed file, 2026-11-15 | Identical to each part's own `eval`, so the replay added no geometry |
| observed | 0 interference at the lid's defaults; 1 candidate pair, intersected, no unchecked pair | `inspect.interference` on `Body`/`Lid`, 2026-11-15 | Boolean intersection, not a tolerance study. Contact faces produce no volume and are therefore invisible to this check |
| observed | The control at `LD_CLEAR` −0.2 reports 5.5004 mm³, bbox X 16.95–17.15, Y 13.90–15.50, Z ±23.38 | Same command with a `parameters.change` step, 2026-11-15 | Proves the check detects a 0.20 mm penetration of the bay wall, i.e. the failure mode it is meant to catch |
| observed | The sleeve's outer wall spans X 16.70–48.30 and the body ends at Y 15.50; the sleeve begins at Y 15.50 | Bounding boxes from `eval` and the lid's own parameter set | Explains the lid README's flagged "0.45 mm overlap above the Pi-bay side": plan overlap, zero depth overlap |
| inference | A real lid would still meet the original's nominal walls | The reconstruction reproduces the envelope and reference edges to 0.000 mm | The R12 lid corners are assumed and the original cavity corners are unknown, so the 0.30 mm inset is not verified against a real part |
| open-question | Whether the Pi, HAT, header, speaker or fastener fits | Nothing but the two printed parts is modelled | Not addressed by this check at all |
| observed | Replaying the lid onto the body needed parameter prefixing and a feature-id offset | First attempt failed with `error: step 29 (timeline.add): feature id 1 is already used` | The body already owns feature ids 1–35; the CLI refuses a duplicate id rather than renumbering |

## Verification

- Exact procedure, from the repository root: the two `sh` blocks in
  [the assembly README](../../models/assemblies/rpispeaker-v17-body-lid/README.md#reproduce-it).
  Both were run verbatim after being written; the first composes and saves
  `/tmp/opencode/v17-body-lid.sc` and re-renders both assets, the second prints
  the default and control interference results.
- Observed results: composition pass; interference pass at defaults; control
  pass (a collision is reported). Physical fit: **not-run** — nothing was
  printed or measured.
- Not tested: printed tolerance, material, screw engagement, sleeve retention,
  acoustics, any component inside either bay, and the original body itself.
  The step that the sleeve rim makes against the divider's front face is a
  coincidence of surfaces and is not a seal or a stop.
- Sanitized artifacts: `models/assemblies/rpispeaker-v17-body-lid/assets/iso.png`
  and `front.png`, rendered from the composed file by `solidcraft-cli snapshot`.

## Handoff and correction links

- Current state: a CAD-only assembly added under `models/assemblies/`, the lid
  and index READMEs updated to cite the measurement. Nothing is printed; no part
  geometry was changed.
- Concrete next action, in order:
  1. James's product decision — does the front panel carry the speaker, or is a
     separate cover wanted? That is the open blocker for the four-screw square
     pattern, and a render of each alternative can be produced with the same
     compose technique.
  2. The speaker itself: frame, depth and four-screw pitch, measured. No
     arrangement can be finished without it.
  3. A Pi Zero 2 W and ReSpeaker HAT envelope composed into the Pi bay would
     answer the next question this assembly cannot: whether the electronics fit
     the reconstructed cavity.
- Authorization needed: printing, purchase and any modification of the original
  body remain outside this note. This note authorizes neither.
- Earlier claims superseded: none. The lid README's "exact lid fit ... is
  unverified" is now narrower, not withdrawn.
- Reviewed report that adopts this: none yet.
