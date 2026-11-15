---
title: RPiSpeaker v17 geometry extracted from the original STEP file
date: 2026-11-15
type: project-learning
status: unreviewed
task: D02
author: OpenCode subagent
author_model: openai/gpt-6.1-terra
author_variant: flex-high
sources:
  - /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.step
  - /home/james/onedrive/Projects/Voice_Assistant/RPiSpeaker/models/Fusion360/RPiSpeaker_v17.f3d
  - tools/cad/step_inspect.py
  - /tmp/opencode/v17tool_iso.png
  - /tmp/opencode/v17tool_front.png
  - /tmp/opencode/v17tool_side.png
  - /tmp/opencode/v17tool_top.png
  - Task handoff with already-completed extraction measurements, 2026-11-15
  - docs/notes/2026-11-15-james-fusion-model-quality-bar.md
supersedes: []
---

# RPiSpeaker v17 extraction

## Summary

This records a previously completed extraction, as supplied in the task
handoff, rather than a new CAD inspection. The source is one AP214 STEP body.
The reported geometry and supplied renders are collected in the
[component reference](../../models/components/rpispeaker-v17/README.md).
This is not a printable reconstruction or a validated design.

The reported body has **no four-screw square speaker mount**. The only
fastener patterns in the solid are four M2.5 pilots at 23 x 58 mm (the Pi Zero
footprint) and two M2.5 pilots 36.5 mm apart in the second bay, so the
remembered square mount is a separate part or a different revision. The present
write-up did
not independently verify the measurements or the earlier `.f3d` scan.

## Claims and evidence

The STEP measurements and scan results in this table are reported by the
task handoff. They are not observations made anew in this documentation pass.

| Kind | Claim | Source | Verification and limits |
| --- | --- | --- | --- |
| measured, 2026-11-15 (coordinator) | AP214; one manifold solid, 513 vertices, 262 `ADVANCED_FACE` entities and 1,552 oriented edges | Re-count of the STEP with `tools/cad/step_inspect.py` | Resolves the earlier 261/262 discrepancy: 262 is correct. The CAD kernel's 143 faces differ because it sews 154 cylindrical STEP patches into 35 faces; plane (76) and cone (9) counts match exactly. |
| reported measurement from STEP | Envelope X 66.15 mm (-17.15 to 49.00), Y 16.10 mm (-0.60 to 15.50), Z 75.30 mm (-37.65 to 37.65) | STEP and extraction handoff | Not independently remeasured. |
| reported measurement and estimate | Volume 15,282 mm³; estimated mass 19.71 g at 1.29 g/cm³; 143 faces (76 plane, 35 cylinder, 9 cone), 419 edges, one shell | STEP and extraction handoff | Method for solid properties and relationship to the STEP counts above were not supplied. Mass is an estimate at the given density, not a measured specimen. `step_inspect.py` does not calculate volume. |
| reported measurement from STEP | Pi Zero bay inner 31.50 × 66.50 mm, X -15.75 to 15.75, Z -32.50 to 34.00; four Ø2.18 mm holes at (±11.5, ±29.0), 23 × 58 mm apart, on Ø4.76 mm bosses | STEP and extraction handoff | Positions are (X, Z). The handoff describes these as M2.5 pilots; fastener fit is not tested. |
| measured, 2026-11-15 (coordinator) | Second bay X 17.15 to 48.25, Z -33 to 33, floor at Y 8.50, so a 31.85 x 66 mm pocket 7 mm deep open toward +Y; two Ø2.18 mm holes at (32.5, ±18.25), 36.5 mm apart, drilled from the back face to Y 7.29, on Ø4.50 mm bosses; one Ø10 mm through hole with a Ø18 mm counterbore at (31.625, 0) opening toward +Y | Re-read of the planar faces with `tools/cad/step_inspect.py` | Hole positions are (X, Z). The pocket depth comes from the Y = 8.50 floor plane and the Y = 15.50 front face, which covers only the Pi bay. |
| reported measurement from STEP | R11 corner rounds; outer wall at X -17.15 is 1.40 mm thick; base recess is 0.60 mm | STEP and extraction handoff | Does not establish other wall thicknesses. |
| measured, 2026-11-15 (coordinator) | A 12.5 mm-wide port window in the Z = -37.65 wall centred at Y 4.5; **three** rectangular cut-outs in the X = -17.15 wall: two 4 x 9 mm at Z 4.75-13.75 and 17.00-26.00, one 5 x 12 mm at Z -26.10 to -14.10 | Re-read of the X = -17.15 planar face and its hole loops | Corrects an earlier "four slots" count. The sizes and spacing match a Pi Zero's two micro-USB and one mini-HDMI connectors, so they read as connector exits, not a speaker grille. |
| reported observation from STEP | No four-screw square speaker mount is present in this body | STEP and extraction handoff | Applies to this body, not to every possible companion part or version. |
| reported observation | The companion `.f3d` has only a 256 px preview and no component or body names; a full byte scan for ASCII and UTF-16 name strings found only `RPiSpeaker v17` | `.f3d` and extraction handoff | Scan method and exact command were not supplied and were not rerun. This does not establish speaker attachment. |
| observed | The supplied PNGs were copied byte-for-byte to the component's `assets/` directory | Four `/tmp/opencode/v17tool_*.png` renders | `file` and `cmp` commands below passed. The views are approximations of the STEP body, not physical evidence. |
| inferred orientation | X is across the bays, Y is depth and up in the isometric rendering, and Z is the long direction shown vertically in the top view | Render images and `step_inspect.py` view projections | Z as device height is a viewing convention, not verified installed orientation. |
| open question | Where the remembered square four-screw speaker mount is | STEP inspection and James's requirement in [the correction](2026-11-15-audio-and-enclosure-corrections.md) | The supplied STEP contains only one solid and no such pattern, so it is either a separate unexported part or another revision. A photo of the assembled original, or the missing lid part, would settle it. This does not block the rest of the enclosure work. |

## Verification

Working directory for these shell commands: `/home/james/Projects/debra`.
The four source images and `tools/cad/step_inspect.py` were also opened with
the file-reading tool. The tool reads STEP entities, reports vertex bounds,
circles and plane offsets, and uses a z-buffered rasteriser for views. Its
parser uses Python's standard library; rendering imports Pillow. Circle
boundaries are not necessarily holes, curved rendering is approximate, and
the tool does not calculate volume.

```bash
file /tmp/opencode/v17tool_iso.png /tmp/opencode/v17tool_front.png /tmp/opencode/v17tool_side.png /tmp/opencode/v17tool_top.png
mkdir -p models/components/rpispeaker-v17/assets
cp -n /tmp/opencode/v17tool_iso.png models/components/rpispeaker-v17/assets/iso.png
cp -n /tmp/opencode/v17tool_front.png models/components/rpispeaker-v17/assets/front.png
cp -n /tmp/opencode/v17tool_side.png models/components/rpispeaker-v17/assets/side.png
cp -n /tmp/opencode/v17tool_top.png models/components/rpispeaker-v17/assets/top.png
cmp /tmp/opencode/v17tool_iso.png models/components/rpispeaker-v17/assets/iso.png
cmp /tmp/opencode/v17tool_front.png models/components/rpispeaker-v17/assets/front.png
cmp /tmp/opencode/v17tool_side.png models/components/rpispeaker-v17/assets/side.png
cmp /tmp/opencode/v17tool_top.png models/components/rpispeaker-v17/assets/top.png
git status --short --untracked-files=all -- models/components/rpispeaker-v17/README.md models/components/rpispeaker-v17/assets/iso.png models/components/rpispeaker-v17/assets/front.png models/components/rpispeaker-v17/assets/side.png models/components/rpispeaker-v17/assets/top.png docs/notes/2026-11-15-rpispeaker-v17-extraction.md tools/cad/step_inspect.py
python3 -B -c 'import pathlib, re, sys; docs=[pathlib.Path("models/components/rpispeaker-v17/README.md"), pathlib.Path("docs/notes/2026-11-15-rpispeaker-v17-extraction.md")]; missing=[str(p.parent / target) for p in docs for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", p.read_text()) if not (p.parent / target).exists()]; print("Missing relative links:", missing); sys.exit(bool(missing))'
```

Observed: `file` identified all four sources as PNGs; all four `cmp` commands
passed with no differences. The relative-link check reported no missing
targets. The targeted Git status showed all six new files and
`tools/cad/step_inspect.py` as untracked; the tool needs coordinator handling
for the reference to work in another checkout. The original render and
extraction commands were not supplied. The component reference gives example
commands for a future inspection, but none were executed for this write-up.

### Not verified

- The STEP geometry, volume, mass estimate, face or edge counts, and `.f3d`
  byte-scan results were not independently checked in this pass.
- The face-count discrepancy is resolved: the STEP has 262 `ADVANCED_FACE`
  entities, and the kernel's 143 faces come from sewing 154 cylindrical patches
  into 35. The
  relation of 1,552 oriented edges to 419 solid edges is also unspecified.
- The original speaker's attachment face or bay, the remembered square mount,
  and the intended installed orientation remain unresolved.
- Wall thicknesses elsewhere, design tolerances, printing history and physical
  fit were not established.
- No CAD, device, network service, printing or fit test was run for this note.

## Handoff and correction links

- Base revision: `ac2298c`; the shared working tree was already dirty. These
  files are an unreviewed documentation handoff, not a completed D02 design.
- Coordinator: review and index this reference, including the discrepancy with
  the [earlier note](2026-11-15-james-fusion-model-quality-bar.md), without
  treating the earlier speaker interpretation as established.
- Further source inspection or physical tests need their own agreed scope; this
  note does not authorize them. No earlier note is superseded by this entry.
