---
title: RPiSpeaker v17 provisional speaker cover bridge
date: 2026-11-15
type: project-learning
status: unreviewed
task: V17 speaker cover
author: OpenCode subagent
author_model: openrouter/openai/gpt-6.1-terra
author_variant: unknown
sources:
  - docs/notes/2026-11-15-rpispeaker-v17-bay-inventory.md
  - models/parts/rpispeaker-v17-body/rpispeaker-v17-body.sc
  - models/parts/rpispeaker-v17-cover/build-script.json
  - models/parts/rpispeaker-v17-cover/rpispeaker-v17-cover.sc
supersedes: []
---

# V17 cover bridge: design and handoff

## Summary

The [new cover](../../models/parts/rpispeaker-v17-cover/README.md) is a
parameter-driven bridge with two feet for the body's measured 36.5 mm pilot
pitch and four **assumed** speaker-mount holes at 32 mm pitch. It is an
unreviewed CAD-only concept, not an identified original piece and not a
demonstrated speaker mounting solution. Nothing was sliced, printed or
fit-tested. The actual speaker's frame, height, square pitch, screw hardware,
contact geometry and wiring are unknown. The next decisive input is a measured
speaker, including its rear footprint and front mounting frame/screw pattern.

## Claims and evidence

| Kind | Claim | Evidence / limitations |
| --- | --- | --- |
| User requirement | A cover should use the two body pilots and carry an adjustable square speaker pattern, with an acoustic opening. | Assigned task, 2026-11-15; does not authorize hardware work. |
| Observed in source | The pilot axes are X 32.5, Z ±18.25, i.e. 36.5 mm pitch; the acoustic axis is X 31.625, Z 0. | [Bay inventory](2026-11-15-rpispeaker-v17-bay-inventory.md), measured STEP; `model.faces` on the reconstruction independently gave both Ø2.1755 core axes and concentric Ø10/Ø18 central axes. STEP cone is Ø20 at Y 2.5 and Ø4.5 at Y 8.5 for each pilot per inventory and body comparison. |
| Hypothesis | A raised bridge can attach at the land, bear against an appropriately shaped speaker on the shelf, and carry four speaker screws. | Geometry only. Default underside Y 17.5 assumes a 15 mm shelf-to-frame height; the bay is too narrow for a full-height 32 mm square rear. The real frame could overhang only if its rear fits and other structures clear it. Screw engagement, retention, sound and assembly are not proven. |
| Observed in CAD | One closed cover, 4,754.507391449257 mm³, bbox X 13.5–51.5, Y 8.5–20.5, Z −23.25–23.25 mm. | CLI `eval` on the saved `.sc`, 2026-11-15; no feature errors and no sketches. |
| Observed in CAD | The reconstructed `Body` and cover yield 0 interferences, one Boolean-intersected pair, none unchecked or truncated. | The [README](../../models/parts/rpispeaker-v17-cover/README.md#rebuild-measure-and-reproduce-checks) has exact reproduction; touching faces are not a positive volume. The reconstruction omits features, and neither physical fit nor Pi/HAT/wiring clearance is established. |
| Observed in CAD | Both foot annuli intersect the reconstruction's land just below Y 8.5 by 0.317029486754 mm³ per 0.01 mm layer. | Probe below; approximately 31.70 mm² contact in model compared with 32.17 mm² for the complete annulus. This is support area, not measured load capacity. |
| Observed in CAD | At X 16.5, Z ±16, Ø2.7 probes extending 4 mm below the bridge each collide with the tall divider by 7.199989 mm³. | Probe below; the default plate is Y 17.5 and the local divider top Y 15.5, leaving only 2 mm of vertical clearance below the plate. Speaker screws/flange/nuts may collide; cover-only clearance is not complete assembly clearance. |
| Observed in CAD | `SQ_PITCH` 32 → 30 → 32 moves the four Ø2.7 axes and restores the default. | README non-saving check: axes (16.5/48.5, ±16) → (17.5/47.5, ±15) → original; volume 4754.507391 → 4475.507391 → 4754.507391 mm³. 14 features recomputed at 30 and 14 restored at 32. Only these settings were checked. |
| Open question | Are the 32 mm pattern, 15 mm height and placement compatible with the actual speaker? | Unknown: measure the rear body, frame, hole pitch and axes, shelf-to-frame height, terminals, hardware and mating part before printing. |
| Open question | Will the anchor fastener actually hold the bridge? | Ø4.6 through-clearance is larger than the Ø2.1755 body core and can pass a small screw head. A washer or appropriate head and tested engagement are needed; neither hardware nor strength is chosen. |

## Verification

From `/home/james/Projects/debra`, the exact cover build, measurement, render,
interference and live-pitch checks are in the cover README. The CLI was used
headlessly throughout; the desktop app and the original open design were not
contacted. The input body `.sc` SHA-256 was
`e48a5ca0d9199501b8cb833fcb4f19f40627830a648c3f1eab9bd5ace6619c74`.

The following temporary annular probes check whether the bottoms of the two
feet sit over actual modeled land, rather than interpreting zero interference
alone as evidence of support. They extend Y 8.49–8.5, with 8 mm outer and
4.8 mm inner diameter. They are deliberately **inside** the body, unlike the
cover, so the two reported intersections are expected:

```sh
python3 -B - <<'PY'
import json, os, subprocess
steps = []
for name, z in [('FootN', -18.25), ('FootP', 18.25)]:
    steps += [
        {'command': 'solid.cylinder', 'params': {
            'name': name, 'body_name': name, 'axis': 'Y',
            'base': [32.5, 8.49, z], 'diameter': 8, 'height': 0.01,
            'operation': 'new'}},
        {'command': 'solid.cylinder', 'params': {
            'name': name + 'Core', 'axis': 'Y', 'base': [32.5, 8.49, z],
            'diameter': 4.8, 'height': 0.01, 'operation': 'cut',
            'targets': [name]}}]
steps.append({'command': 'inspect.interference',
              'params': {'bodies': ['Body', 'FootN', 'FootP']}})
fd = os.memfd_create('foot-contact', 0)
os.write(fd, json.dumps(steps).encode())
r = subprocess.run(['solidcraft-cli', 'run', f'/proc/self/fd/{fd}',
                    '--in', 'models/parts/rpispeaker-v17-body/rpispeaker-v17-body.sc',
                    '--results'], pass_fds=(fd,), check=True,
                   capture_output=True, text=True)
print(json.dumps(json.loads(r.stdout)[-1], indent=2))
PY
```

Result: Body/FootN 0.31702948675362 mm³ and Body/FootP
0.3170294867535847 mm³; 2 intersections, 2 pairs Boolean-intersected,
0 unchecked, not truncated. These probes are not the cover/body interference
test and intentionally do overlap the body.

To test a possible screw envelope, two Ø2.7 mm cylinders span Y 13.5–17.5
under the X-negative square holes. This is an intentionally generic 4 mm
projection, not a model of a selected screw or the actual speaker:

```sh
python3 -B - <<'PY'
import json, os, subprocess
steps = []
for name, z in [('SquareLeftN', -16), ('SquareLeftP', 16)]:
    steps.append({'command': 'solid.cylinder', 'params': {
        'name': name, 'body_name': name, 'axis': 'Y',
        'base': [16.5, 13.5, z], 'diameter': 2.7, 'height': 4,
        'operation': 'new'}})
steps.append({'command': 'inspect.interference',
              'params': {'bodies': ['Body', 'SquareLeftN', 'SquareLeftP']}})
fd = os.memfd_create('speaker-screw-probe', 0)
os.write(fd, json.dumps(steps).encode())
r = subprocess.run(['solidcraft-cli', 'run', f'/proc/self/fd/{fd}',
                    '--in', 'models/parts/rpispeaker-v17-body/rpispeaker-v17-body.sc',
                    '--results'], pass_fds=(fd,), check=True,
                   capture_output=True, text=True)
print(json.dumps(json.loads(r.stdout)[-1], indent=2))
PY
```

Result: two intersections, 7.199989200356277 and 7.199989200356271 mm³;
2 pairs Boolean-intersected, 0 unchecked, not truncated. Each intersection spans
Y 13.5–15.5 at the divider, so screw length, frame/nut locations, and actual
fit require attention before a print.

Documentation check: `python3 -B -m unittest tests.test_docs -v` from the
repository root, 2026-11-15: 11 tests ran in 0.083 s, **OK**, including image
references and model-folder links. `git diff --check` also returned no output;
that Git check does not inspect these untracked files.

## Handoff

- Base when work began: `cd4790f0135f53588997a175f804a73f8cfbf230`, on `main`;
  an unrelated untracked `tools/notices.py` was present and was not edited.
- A separate capable reviewer should check the candidate, especially whether
  the proposed bridge/clamping concept is useful for the actual speaker and
  whether the Ø4.6 clearance, counterbores and intended fasteners are sensible.
- Confirm the physical speaker's complete dimensions and its four-screw
  mounting, including how screws engage; then update parameters and rerun
  collision/fit checks before considering a print. Printing, device changes,
  hardware testing, and coordinator integration need their own authorization.
- No changes were made to the body file, the open desktop document, or other
  assigned-out paths. This note does not supersede earlier notes or authorize
  a print.
