---
title: The device page needs JavaScript, and discovery needs avahi-utils
date: 2026-11-16
type: project-learning
status: unreviewed
task: none
author: OpenCode coordinator session
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - User statement, 2026-11-16, that Chrome on his computer had JavaScript disabled
  - Observed on debra-8518d6 (Pi Zero 2 W), 2026-11-16
  - control/web/server.py, control/web/assets/app.js, control/web/discovery.py at 44c8f24 plus the uncommitted web-auth fix
  - https://manpages.debian.org/trixie/avahi-utils/ (package provides avahi-browse)
supersedes: []
---

## Summary

Two dependencies of the device page were not declared where a person installing
it would look. **The page requires JavaScript**: with scripting off, no probe
runs, the bypass button stays hidden, and the key form submits natively to
`/?key=...`. **Discovery requires `avahi-browse`** (Debian package
`avahi-utils`), which was absent from the Zero 2 W even though `avahi-daemon`
was running. Both failures are now visible on the page, and the package gap is
recorded here and in the web README; neither is enforced by an installer.

## Claims and evidence

| Kind | Claim | Source / date / hardware-version scope | Verification and limits |
| --- | --- | --- | --- |
| observed | A browser with JavaScript disabled sees the welcome card with no bypass button, and a form submit becomes `GET /?key=...`. | James's Chrome, 2026-11-16; debra-8518d6 | Reported by the user and consistent with the code path (`start()` never ran). Not measured in that browser by this session. |
| observed | `avahi-daemon` was active but `avahi-utils` was not installed, so `avahi-browse` was missing and `/api/devices` reported `Discovery problem: avahi-browse is not installed`. | debra-8518d6, 2026-11-16 | `dpkg -l avahi-utils` empty; `command -v avahi-browse` empty. |
| observed | After `apt-get install -y avahi-utils`, discovery returned the Pi 5. | debra-8518d6, 2026-11-16 | `GET /api/devices` → `discovery.found: 1`, `error: null`, device `debra-3c6b3f`. |
| observed | ZRAM is active and correctly reported on this device (`zram0: 33.1 MiB data → 11.7 MiB RAM`); `zramctl` and `swapon` binaries are absent but the page reads sysfs. | debra-8518d6, 2026-11-16 | `/proc/swaps` lists `/dev/zram0`; the rendered dashboard row matched `/sys/block/zram0/mm_stat`. |
| hypothesis | A fresh Zero 2 W image built by hand will also lack `avahi-utils` unless the build adds it. | Inferred from the absence on this image | Not tested on a second card. |

## Verification

- Exact safe commands/procedure and working directory:
  - On the device: `command -v avahi-browse`, `dpkg -l avahi-utils`,
    `systemctl is-active avahi-daemon`, then `sudo apt-get install -y avahi-utils`
    and `curl -s http://127.0.0.1:8787/api/devices`.
  - From the development host: a fresh-profile headless Chromium run of the page
    with and without `#key=`, checking `#dashboard`, `#pair`, `#bypass`.
- Observed results: pass — discovery `found: 1`, `error: null`; the page renders
  the ZRAM row from the device's own status.
- Not tested, conflicting evidence, and remaining uncertainty: the user's exact
  Chrome version and settings were not inspected; the JavaScript requirement is
  now stated by the page's `<noscript>` text, but no browser test runs with
  scripting disabled.
- Sanitized artifact references: `docs/testing/results/2026-11-16-zero2w-web-portal-and-hat-audio.md`
  (Addendum 2).

## Handoff and correction links

- Current state and relevant base/candidate revision: device page running
  `--auth none` from the uncommitted web-auth fix (release `078eb64b…`); web
  README now lists `avahi-utils` and JavaScript as prerequisites.
- Concrete next action and prerequisites: the setup/device-build path should
  declare or install `avahi-utils` when discovery is expected to work. The web
  installer deliberately installs no packages, and `control/setup/` is another
  worker's packet with uncommitted changes, so this session did not change
  either. Decide whether a device build manifest (like `tools/device/lab-pi5/`)
  should own the package list for the Zero 2 W.
- Authorization needed; do not treat this suggestion as permission: installing
  packages on other boards or adding package installation to an installer.
- Earlier claim superseded, if this is a correction: none.
- Reviewed report/decision that later adopts this finding, if known: none yet.
