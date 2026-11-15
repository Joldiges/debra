---
title: The v17 cover intersects the lid, so the two cannot be assembled together
date: 2026-11-15
type: project-learning
status: unreviewed
task: V17 speaker cover
author: OpenCode coordinator
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - models/parts/rpispeaker-v17-cover/rpispeaker-v17-cover.sc
  - models/parts/rpispeaker-v17-cover/build-script.json
  - models/parts/rpispeaker-v17-lid/rpispeaker-v17-lid.sc
  - models/parts/rpispeaker-v17-body/rpispeaker-v17-body.sc
  - docs/notes/2026-11-15-v17-cover-design.md
  - docs/notes/2026-11-15-rpispeaker-v17-bay-inventory.md
supersedes: []
---

# The cover and the lid occupy the same space

## Summary

The [provisional cover](../../models/parts/rpispeaker-v17-cover/README.md) was
checked against the body and not against the lid. Against the
[lid](../../models/parts/rpispeaker-v17-lid/README.md) it intersects by
**785.083645226661 mm³** in one Boolean-intersected pair, with no unchecked
pairs and no truncation. The two parts cannot be fitted together as they stand.

This does not say the cover is wrong in isolation. It says the cover and the lid
are two front plates over one bay, and only one of them can be there.

## The measurement

Run from the repository root. Both designs define the same parameter names, so
the cover's parameters are prefixed `CV_` before they are replayed on top of the
lid; the cover's geometry is unchanged by that rename.

```sh
python3 -B - <<'PY'
import json, os, re, subprocess

cover = json.load(open('models/parts/rpispeaker-v17-cover/build-script.json'))
params = [c['params']['name'] for c in cover['commands'] if c['command'] == 'parameters.add']

def rename(value):
    if isinstance(value, str):
        for name in params:
            value = re.sub(rf'\b{re.escape(name)}\b', 'CV_' + name, value)
        return value
    if isinstance(value, list):
        return [rename(v) for v in value]
    if isinstance(value, dict):
        return {k: rename(v) for k, v in value.items()}
    return value

steps = []
for command in cover['commands']:
    step = {'command': command['command'], 'params': rename(command['params'])}
    if command['command'] == 'parameters.add':
        step['params']['name'] = 'CV_' + command['params']['name']
    steps.append(step)
steps.append({'command': 'inspect.interference', 'params': {'bodies': ['Lid', 'Cover']}})

fd = os.memfd_create('cover-vs-lid', 0)
os.write(fd, json.dumps(steps).encode())
r = subprocess.run(['solidcraft-cli', 'run', f'/proc/self/fd/{fd}',
                    '--in', 'models/parts/rpispeaker-v17-lid/rpispeaker-v17-lid.sc',
                    '--results'], pass_fds=(fd,), check=True, capture_output=True, text=True)
print(json.dumps(json.loads(r.stdout)[-1], indent=2))
PY
```

Result, as reported by the CLI:

| Field | Value |
| --- | --- |
| Intersections | 1 |
| Volume | 785.083645226661 mm³ |
| Contact area | 1560.885529275955 mm² |
| Bounding box | X 16.7–48.3, Y 8.5–20.5, Z −22.25–22.25 |
| Pairs | 1 candidate, 1 intersected, 0 not checked, not truncated |

## Where the two parts overlap

Three separate collisions, all of them expected from the two designs:

- **The two Ø8 feet** rise from Y 8.5 to 17.5 on the pilot axes (X 32.5,
  Z ±18.25). The lid's rear screw pads occupy the same axes from Y 8.5 to 13.9,
  with only a Ø2.1755 screw hole through them. A Ø8 foot cannot pass through a
  Ø2.1755 hole.
- **The cover's plate** sits at Y 17.5–20.5. The lid's plate is at Y 13.9–15.5,
  so the plate does not touch it, but the lid's **sleeve** protrudes to Y 25.50
  and is pierced by the cover's plate.
- **The acoustic openings do not line up in depth**: the cover's Ø20 hole is at
  Y 17.5–20.5, the lid's Ø28.4 aperture at Y 13.9–15.5. One is in front of the
  other, so together they are two apertures in series, not one.

## What this means for the four-screw pattern

The body has no square pattern and only the two Ø4.5 pilots. The lid is held by
those same two pilots — its own holes are on the same axes at Y 8.5 — and it
already carries a speaker provision: a Ø28.4 aperture, a Ø24.8 rear opening, and
a sleeve for an assumed Ø28 × 10 mm bare driver on a 1.6 mm radial land.

That makes a **separate** cover unlikely to be the original arrangement. The more
plausible reading is that the front panel *is* the speaker carrier, and the
four-screw square pattern belongs in that panel. It cannot be confirmed from the
geometry: a 32 mm square pitch does not fit a Ø28 driver, so the pattern would
have to belong to a different, larger speaker than the one the lid currently
assumes.

Neither reading is proven. What is proven is that the current cover and the
current lid cannot both be installed.

## What is not established

- No physical part was measured, printed or fitted.
- The lid itself is a reconstruction with assumed R12 corners, an assumed
  connector slot and an assumed bare driver. Its sleeve overlap with the Pi bay
  is already flagged as unchecked in its own README.
- The interference is computed against those reconstructions. A real lid with
  the same nominal dimensions would still collide, because the collision is
  structural — a foot through a pad, a plate through a sleeve — not a tolerance
  effect.

## Next step, in order

1. Decide whether the front panel or a separate cover carries the speaker. That
   is a product decision, not a measurement.
2. If the panel carries it, add the four-screw pattern to the lid and delete the
   cover concept, rather than maintaining two parts that cannot coexist.
3. If a separate cover is wanted, the lid's speaker region has to be opened up
   first, and the cover's feet have to be reduced to the pilot clearance so they
   pass through the lid's pads.
4. Either way, the speaker's real frame, height and screw pitch still have to be
   measured. Nothing here substitutes for that.
