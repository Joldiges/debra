# Three devices, three builds, and no page that could say which

**2026-11-16.** James asked for the three testbench Pis and the development host
to be brought to the same web-server version, and for the page to report version
identifiers. This note records what was found before any device was changed.

Author: OpenCode session, `openrouter/deepseek/deepseek-v4.1-flash-1017`, variant
not exposed by the host. Host: Fedora.

## Method

No device was logged into and nothing was installed. Each running server was
identified by fetching the three assets it serves (`/`, `/app.js`,
`/style.css`) and comparing their SHA-256 to the same files at every commit that
touched `control/web/assets`. Two independent matches are reported below as
commit matches; anything else is described as "no commit matches", which is a
negative result, not an inference about what the device is running.

## What each endpoint serves

| Endpoint | Board | Auth mode | Served assets match | Meaning |
| --- | --- | --- | --- | --- |
| `debra-3c6b3f.local:8787` | Pi 5 Model B (lab device) | `none` | `efcad08` (2026-11-15) | Oldest build in service; behind `main` by several commits. |
| `debra-f943dc.local:8787` (192.168.0.70) | Not established | `key` (401 on `/api/status`) | `e4b16e0` (2026-11-15), identical assets to `ba0b0e4` | **Current with committed `main`.** Discovers `debra-3c6b3f`. Not described anywhere in this repository. |
| `debra-8518d6.local:8787` | Pi Zero 2 W | `none` | No commit matches: `style.css` and `index.html` equal the **live working tree**, `app.js` is an earlier draft of it | A snapshot of the other session's uncommitted UI pass, taken part-way through it. |
| `127.0.0.1:8787` (host) | Development host | `none` | `app.js` and `style.css` equal the live working tree; `/index.html` returns a JSON 404 | **Half-updated.** The process started 2026-11-15 15:30 and reads assets from disk per request, so it serves new assets with the `STATIC` map it loaded hours earlier. |

The host row is the concrete failure this work exists to prevent: a process can
serve changed files while running old code, and nothing on the page said so.

## Why the release digest is the version identifier

`control/web/install.py` already names each release directory by the SHA-256 of
exactly the five files in `PAYLOAD` (`payload_digest`). That value cannot drift
from the bytes it describes, is already written into the unit's `ExecStart`, and
is what `--restore` validates. Nothing was invented: the page now reports a
number that already existed but was only visible to someone reading a unit file.

## What was changed, and what was not

- A version report was added on branch `web/version-id` (`b6e9aef`), in a
  separate worktree: `PAYLOAD` and `payload_digest` moved to `server.py` and
  `install.py` imports them, `/api/status` gained `version.{release,short,
  on_disk,restart_required}`, and the footer shows `Build <short>` with the full
  digest on hover.
- **No device was updated.** `debra-3c6b3f` and `debra-f943dc` reject the host's
  SSH keys for every account tried (`debra`, `james`, `pi`, `admin`, `root`,
  `dietpi`), so neither can be reached without credentials. `debra-8518d6` and
  the host's process are the other session's live development targets; replacing
  them would revert work in flight.
- The branch is deliberately **not merged**: the other session holds uncommitted
  changes in `control/web/server.py`, `assets/*` and `tests/test_web*.py`, and a
  commit from this checkout would either take their work or be reverted by it.

## Verification and limits

Verified offline: 153 web+install tests, 816 offline, 23 browser, and a live run
whose `/api/status` digest equals the release id the installer writes for the
same tree. The footer line was checked by screenshot only, not by a browser
assertion.

Not verified: no card, radio, SSH, systemd or browser session against any of the
three devices. The device rows above are HTTP responses and Git blob matches,
nothing more. `debra-f943dc`'s board model is unknown because its status needs a
key this host does not have.

## Outcome, added the same day after the updates

The sections above are the pre-change snapshot and are left as written. What
happened next:

| Endpoint | Release now | Note |
| --- | --- | --- |
| `debra-3c6b3f` (Pi 5) | `293f4e001c84…` | Updated twice: first to branch `web/version-id`, then to merged `ea825e5`. `/api/status` reports `version.short` and `restart_required: false`. |
| `debra-f943dc` | `9f532517e4fe…` | Untouched. At the `main` of the time; now behind the merge. |
| `debra-8518d6` | `054631e3a7ab…` | Untouched. Changed under this session during the work: the other session redeployed it twice. |
| host `127.0.0.1:8787` | `293f4e001c84…` | Restarted twice from the shared checkout: first to make it coherent with its own tree, then after the merge, which is what put the build line on it. |

`debra-f943dc` is a **Raspberry Pi Zero W Rev 1.1, `armv6l`**, running the web
server on Raspbian 13 with Python 3.13.5. That is the first evidence that this
prototype runs at all on ARMv6; it is not evidence about audio, the HAT, or the
setup service there.

### A false "damaged" report blocked the rollback it was warning about

Deploying to the Pi 5 printed `damaged_releases` naming both of its retained
releases, and "rolling back to one would start a broken service". Both are
intact: they were installed before `discovery.py` joined `PAYLOAD`, so they hold
four files, and their `server.py` never imported it — one had been running for a
day. `release_digest` hashed today's five-file list, raised `OSError` on the
absent file, and `release_problem` ran the same checklist, so `--restore` refused
both. The check now hashes the files actually in the directory, and the digest is
the completeness proof. Fixed in `a411d45`; both units are now reported
RESTORABLE on the device.

This is the second time in two rounds that a guard protected against the wrong
thing by assuming today's shape is the only valid one. It is worth asking of
every remaining check: *whose* payload does it assume?

### Limits

No rollback was performed, only shown to be permitted. Nothing was installed on
`debra-f943dc` or `debra-8518d6`; both are now behind the merge and one command
away. The version report was checked on the Pi 5 and the host through
`/api/status`; the footer line was seen rendering only against the synthetic
fixture, because the device page opens on its key card and nothing here clicked
through it.

