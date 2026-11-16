---
title: Web dashboard refreshed on all three Debras
date: 2026-11-16
type: test-result
status: unreviewed
task: control-ui
author: OpenCode coordinator
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - "commit 644b8ef402aa (page payload) installed from the checkout at 18e4ad7/662c919"
  - "systemd user unit debra-web.service on each device"
supersedes: []
---

## Summary

James asked for the latest dashboard on all three Pis, which supersedes the
earlier restriction to the host and the Pi 5. All three now run the same page
payload, `644b8ef402aa`, and each was verified after restart. `debra-f943dc`
kept its `--auth key` mode: that check is the one that would have mattered if it
had gone wrong, so it was verified explicitly rather than assumed.

| Device | Board | Access mode | Build | Service | Page | Audio sink |
| --- | --- | --- | --- | --- | --- | --- |
| `debra-3c6b3f` | Pi 5 Model B Rev 1.0 | `--auth none` (keyless) | `644b8ef402aa` | active | 200 | `alsa_output.platform-soc_107c000000_sound.stereo-fallback` |
| `debra-8518d6` | Pi Zero 2 W Rev 1.0 | `--auth none` (keyless) | `644b8ef402aa` | active | 200 | `alsa_output.platform-soc_sound.stereo-fallback` |
| `debra-f943dc` | Pi Zero | `--auth key` | `644b8ef402aa` | active | 200 | `alsa_output.platform-soc_sound.stereo-fallback` |

## How it was done

For each device: the committed `control/web/` was copied to
`/tmp/debra-web-stage/control/web/`, `install.py` was run **with that device's own
flags** read from its current unit, the new unit was diffed against the preserved
previous unit, and only then was the service restarted.

- Every unit diff showed **only the release path** under
  `~/.local/share/debra/web/releases/`; bind, port, sink, auth mode and allowed
  hosts were unchanged on all three.
- `install.py` preserved a previous unit for each
  (`previous-units/2026111…service`), which is the rollback path.
- Releases retained after the change: 9 on `debra-3c6b3f`, 4 on
  `debra-8518d6`, 2 on `debra-f943dc`.
- Disk was checked first: every device has more than 19 GB free and a release is
  under 400 KB.

## Observed during the change

| Kind | Observation | Evidence |
| --- | --- | --- |
| observed | `debra-f943dc` reported the unit as `active` for about 7 seconds before anything was listening on 8787, then served normally | `curl` failed with connection refused at first; the journal shows "Debra web prototype listening" 7 s after start. A Zero is slow to start — waiting for the port, not for `is-active`, is the correct check |
| observed | `debra-f943dc` still returns 401 on `/api/status` without a key and 200 on the page, so key mode is intact | `curl` after restart |
| observed | The new page markers (`section-nav`, `keyless-lead`, `power-gaps`, `page-footer`) are present in the served HTML on all three | `curl` + grep |

## Limits

- Nothing was audible: no test sound, no volume change, no mute change. The audio
  column is the sink each unit names, not proof that it works.
- The two keyless devices were not exercised beyond the keyless probe; no key
  was entered on `debra-f943dc`, so its authenticated views are unverified on
  that board.
- The host's page is served by a foreground `server.py` process rather than a
  unit, so its build string is unknown until that process is restarted; its
  assets are current because they are read from disk per request.
