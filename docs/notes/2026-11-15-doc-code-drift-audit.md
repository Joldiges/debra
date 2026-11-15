---
title: Doc-code drift audit of the web controls and the tooling guides
date: 2026-11-15
type: project-learning
status: unreviewed
task: WEB
author: OpenCode subagent
author_model: openrouter/deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - control/web/README.md at 84411f8
  - control/web/server.py at 84411f8
  - control/web/install.py at 84411f8
  - control/web/assets/app.js at 84411f8
  - control/web/assets/index.html at 84411f8
  - docs/design/web-control.md at 84411f8
  - docs/development.md at 84411f8
  - docs/guides/current-status.md, getting-started.md, scheduled-runner.md, device-backup.md, pi5-lab-preparation.md at 84411f8
  - tests/test_web.py and tests/test_web_browser.py at 84411f8
  - tools/discover.py, tools/activity.py, tools/taskchain.py, tools/scheduled_runner.py at 84411f8
---

# Doc-code drift audit: web controls and tooling guides

Claim by claim, the prose was compared with the source. Nothing was edited, run
against a port, or sent to a device.

## Snapshot, method and limits

**Line numbers refer to commit `84411f8`**, not to the working tree. The working
tree changed under this audit: `main` advanced from `84411f8` to `9c9383d`
("Show discovered Debra devices in the hub, from one parser") while I was
reading, landing the mDNS discovery work that had been uncommitted. I extracted
`git archive 84411f8` to `/tmp/opencode/audit-84411f8` and cited that copy, so
every reference below is reproducible with
`git show 84411f8:<path> | sed -n '<line>p'`. Each claim column quotes a few
words so a reader can relocate a row after the lines move.

Direction is used strictly:

- **overclaim** — the document says a behaviour the code does not have;
- **undocumented** — the code does something the document does not mention,
  especially writing, spawning, crashing, or widening access;
- **correct** — traced to implementing code (listed separately below).

I read the tests but did not execute them. `tests/test_web.py` binds loopback
sockets, which the instruction for this task excludes; evidence for test-shape
claims is therefore the test source, not a run.

## Overclaims (4)

| Claim (file:line) | Code reality (file:line) | Direction | Severity |
| --- | --- | --- | --- |
| `docs/guides/scheduled-runner.md:34,48` — run directory and report path are "`.local/runner/runs/<day>-<id>/`" | The directory is `<day>-<8 hex>`, from `uuid.uuid4().hex[:8]`, not the task id; only file names inside use the id (`tools/scheduled_runner.py:419`, `:233-234`, `:287`) | overclaim | Low |
| `docs/guides/scheduled-runner.md:33` — `activity.log` holds "one JSON line per finished task" | Two lines per task: `{"event": "start" ...}` and `{"event": "finish" ...}` (`tools/scheduled_runner.py:421`, `:438`) | overclaim | Low |
| `docs/guides/scheduled-runner.md:36` — `.local/runner/prompts/` listed as runner state, "prompt files, one per task" | `ensure_layout()` creates only the runner directory, `runs/`, `config.json`, `queue.json`, `state.json` (`tools/scheduled_runner.py:123-131`); the token `prompts` appears nowhere in the module, and `--prompt-file` just reads the given path (`:326-327`) | overclaim | Low |
| `docs/design/web-control.md:426` — "returns **only** partial systemd enabled/running evidence for named LVA, Sendspin and user/system Snapcast units" | `SERVICES` also probes `pipewire.service` and `wireplumber.service`, in the same namespaces (`control/web/server.py:32-39`, `:233-236`) | overclaim (undercount) | Low |

**`control/web/README.md` itself has zero verified overclaims at this commit.**
Every numbered claim in it — including the ones that have drifted before — is
backed by the code below. That is a result, not a gap in the audit: the
priorities named for this task were traced individually.

## Undocumented behaviours (10)

| Claim (file:line) | Code reality (file:line) | Direction | Severity |
| --- | --- | --- | --- |
| `control/web/README.md:134` — `hardware.json` is "Optional retained `hat`/`speaker` string labels", presented as inert | The file is parsed with a bare `json.loads` at startup (`control/web/server.py:594`); only the *shape* check that follows gets `parser.error` (`:595-597`). Malformed JSON, bad encoding or a permission error escapes as a traceback, and the generated unit is `Restart=on-failure` / `RestartSec=3` (`control/web/install.py:128`), so one bad character becomes a restart loop | undocumented | Medium |
| `docs/guides/current-status.md:10-18` — "Available now" lists only written guidance, notes, the task helper and historical backup scripts; line 8 dates the page to the 2026-11-14 baseline | At `84411f8` the checkout also contains the tested browser slice (`control/web/README.md:1-7`, `control/web/server.py`), its installer (`control/web/install.py`), and the CAD models (`models/`). Two other docs already point at them (`docs/README.md:32`, `docs/guides/getting-started.md:41`) | undocumented (understates what exists) | Medium |
| `control/web/assets/index.html:17` — keyless warning: "Anyone who can reach it can change its **volume**" | `--auth none` also accepts mute writes and full status reads, because the whole `/api/*` key check is skipped when the token is `None` (`control/web/server.py:387-395`, `:404-405`, `:329-333`); the README states this correctly at `:35-37` | undocumented (security notice understates exposure) | Low |
| `control/web/README.md:35` and `:132` — `--auth none` is an installer option; `access.key` is "the persistent device key" | `install()` calls `init_state(state)` unconditionally before choosing the auth mode (`control/web/install.py:91`), so a keyless install still creates an owner-only `access.key` that the server then never reads (`control/web/server.py:583-590`) | undocumented (a write not described) | Low |
| `control/web/README.md:31-34` — the public surface in key mode is named as `GET /api/devices` | Two others are public: `/`, `/app.js`, `/style.css` are served before any key check (`control/web/server.py:387`, `:401-403`), and `/api/status` carries an `auth` field the page depends on (`:409`, `control/web/assets/app.js:360`) which the README never mentions (the design doc does, `docs/design/web-control.md:208`) | undocumented | Low |
| `control/web/README.md:73-86` — install example with `--port 8787` | The installer enforces two rules the README does not state: the port must be 1024–65535, and *every* `--host` port must equal it (`control/web/install.py:69-71`) | undocumented | Low |
| `control/web/README.md:155-160` — "Each entry has a `name`, `url` and optional `label`" | Undocumented limits: ≤50 entries, name ≤64 chars, label ≤80, URL ≤200 (`control/web/server.py:528`, `:535`, `:543`, `:495`) | undocumented | Low |
| `control/web/README.md:13` — "polling ... never restore or set volume"; no statement about caching | Most of the status payload is cached for 2 s, while audio is deliberately re-read every time (`control/web/server.py:289-291`). Only the design doc records this (`docs/design/web-control.md:138`) | undocumented | Low |
| `control/web/README.md:84-85` — loopback install "uses `--bind 127.0.0.1` and `--host 127.0.0.1:8787`" | The server has a default the README never mentions: with no `--host` and a loopback bind, it admits `127.0.0.1:<port>` by itself (`control/web/server.py:574`); the installer is stricter and requires `--host` (`control/web/install.py:159`) | undocumented | Low |
| `docs/guides/scheduled-runner.md:34-35` (table of runner state) | The overlap lock `.local/runner/run.lock` is real state the runner creates and clears (`tools/scheduled_runner.py:45`, `:163-192`) but is absent from the table, though line 12 mentions "a lock file" | undocumented | Low |

## Verified correct (not skin-deep)

Traced to implementing code, including the four priorities named in the task.

1. **`GET /api/devices` is genuinely public in key mode.** `README.md:31-34`
   ↔ `server.py:387` (`self.path != "/api/devices"` exempts it from the bearer
   check), `:404-405` (served with the configured list). It still requires the
   Host and same-origin checks, exactly as the README says. Fixture:
   `tests/test_web.py:283`.
2. **`--auth none` really is a total bypass** — status reads *and* writes.
   `README.md:35-37` ↔ `server.py:310` ("every request then carries no
   authentication"), `:583-590` (token stays `None`), `:387-395` (check skipped
   when `token is None`); unit argument asserted at `tests/test_web.py:729`.
3. **The 15-second overall deadline is one constant, used three ways.**
   `README.md:46` ↔ `REQUEST_TIMEOUT = 15` (`server.py:40`) → `Server.request_timeout`
   (`:306`) → per-request `deadline` and the shutdown timer (`:334-340`) and
   `remaining()` (`:52-56`), which bounds lock waits (`:185-193`) and re-checks
   after the availability probe so an expired queued write cannot start
   (`:223-228`). Fixtures: `tests/test_web.py:197`, `:206`, `:369`, `:403`.
4. **"Four fixed runtime files" is exactly true.** `README.md:59-60` ↔
   `PAYLOAD` of four entries (`install.py:21`), asserted against the published
   release contents at `tests/test_web.py:655-663`.
5. **Permissions are enforced where the README says.** `README.md:132,139`
   ↔ state dir must be owned and `0700` (`server.py:449-450`, `:473`); key must
   be a regular file, owned, `0600`, `O_NOFOLLOW`, ≤129 bytes (`server.py:475-480`);
   install directories owned, private ones `0700` (`install.py:38-41`), release
   files `0600` (`:110`), device list `chmod 0600` (`:62`), unit and backups
   `0600` (`:142`, `:148`). Fixture: `tests/test_web.py:574-582`.
6. **Everything the README promises about rollback is actually implemented.**
   `README.md:173-189` ↔ previous unit copied before atomic replace and its path
   returned (`install.py:132-151`); old releases and old device lists are never
   deleted (`install.py:95-100`, `:44-63`). Fixtures restore a previous unit and
   its list byte-for-byte (`tests/test_web.py:667-676`, `:749-768`).
7. **The documented legacy `devices.json` caveat is true of the code history.**
   `README.md:184-185` ↔ commit `70cd23b` replaced `state / "devices.json"`
   (`install.py` before that commit) with `store_devices()` (`install.py:44-63`);
   regression fixture `tests/test_web.py:792-805`.
8. **The unit never contains the key.** `README.md:136` ↔ arguments built from
   `--state-dir` only (`install.py:112-120`); asserted by
   `tests/test_web.py:660` (`assertNotIn(key, unit)`).
9. **The installer reports what the README lists and prints no key.**
   `README.md:87-88` ↔ returns `release`, `unit`, `previous_unit`, `changed`
   (`install.py:134`, `:150-151`) printed verbatim (`:179-180`).
10. **Device-list URL grammar matches the prose, on both sides.**
    `README.md:155-160` ↔ `canonical_device_url()` lowercases host and scheme,
    forces a trailing slash, rejects paths/queries/userinfo/whitespace
    (`server.py:492-516`) and the page re-applies the same shape before
    rendering a link (`assets/app.js:309-321`).
11. **Test claims are accurate.** `README.md:195-202` ↔ the browser module is
    opt-in via `DEBRA_BROWSER_TEST`, located with `shutil.which`
    (`tests/test_web_browser.py:20`, `:498-499`) and launched **without**
    `--no-sandbox` (`:511-517`), against synthetic responses only (`:520-529`).
12. **"No status release-ID field" is true.** `README.md:110` ↔ the status
    payload has no release field (`server.py:285-300`); the design doc's "caches
    most status for two seconds" (`design/web-control.md:138`) matches
    `server.py:289`.
13. **Design-doc `Current` rows are accurate about the payload**: `hostname`
    (`:204` ↔ `server.py:294`), `detected_hat`/`model` (`:290-291` ↔ `:158-159`),
    `selected_hardware` labels only (`:292-293` ↔ `:296`, `:591-597`),
    `unit_found`/`enabled`/`active`/`configuration` (`:351-354` ↔ `:249-256`),
    no timestamps (`:362`), CPU from two samples (`:443` ↔ `:108-112`), storage
    from the server root (`:445` ↔ `:152-155`), Wi-Fi null outside −127..0
    (`:446` ↔ `:146`), no core voltage (`:447`), `EXT5V_V` only (`:448` ↔
    `:389-395`), zram/zswap fields (`:454-455` ↔ `:130-138`, `:164-165`).
14. **`docs/development.md` claims check out**: `.local/` ignored
    (`:13` ↔ `.gitignore:5`), owner-only in this checkout (`.local` is `0700`
    on disk), `.env` handling (`:53` ↔ `.gitignore:8-11`), claims live in
    `<git-common-dir>/debra-work` (`:27` ↔ `tools/taskchain.py:390`), and no
    submodule or `upstream/` exists yet (`:120-122`).
15. **`docs/guides/getting-started.md` commands exist**: `taskchain.py check`
    (`:137` ↔ subcommands at `tools/taskchain.py:366`), the full-suite and
    `DEBRA_BROWSER_TEST` invocations (`:138`, `:145` ↔ the same opt-in guard),
    and "web rollback is fixture-tested only" (`:44` ↔ `tests/test_web.py:749`).
16. **`docs/guides/scheduled-runner.md` rules are implemented**: default
    `daily_budget_usd: null` (`:21` ↔ `tools/scheduled_runner.py:49`), guardrail
    text appended to every prompt (`:14-18` ↔ `:62`, `:202`), one task and one
    lock (`:12-13` ↔ `:414-417`), no `--auto` anywhere in the module (`:19` ↔
    the only occurrence is the docstring at `:12`; the process is launched at
    `:242`), everything under `.local/runner/` (`:24` ↔ `:41-45`).

## Unclear (3)

1. `docs/guides/scheduled-runner.md:59-60,86-87` — timer cadence ("one minute
   after boot, then one minute after each run finishes") and "Linger is off".
   These live in user units outside the repository, which the page says
   explicitly (`:54-55`). *Would settle:* `systemctl --user cat
   debra-runner.{service,timer}` and `loginctl show-user $USER -p Linger`.
2. `control/web/README.md:55` — "Python 3.10+" is stated as a prerequisite but
   nothing in the code enforces or documents a version floor; I found no
   3.10-only syntax in `server.py` or `install.py`, so I cannot tell whether the
   floor is measured or assumed. *Would settle:* a recorded interpreter check on
   the device, or a stated reason in the code.
3. `control/web/README.md:184-185` — code and history confirm that units from
   before `70cd23b` pointed at a shared `devices.json` (so the warning is
   sound), but this checkout cannot show whether any real device ever ran such
   a unit. *Would settle:* the device's retained `previous-units/` entries.

## Answering the four priorities directly

- **`--auth none`**: README correct (`:35-37`); the page's own note
  (`index.html:17`) understates it by naming only volume. No authentication
  bypass exists in key mode.
- **`/api/devices` in key mode**: correctly described as public
  (`README.md:31-34` ↔ `server.py:387`, `:404-405`).
- **Polling and timeout numbers**: at this commit the README states exactly one
  figure, 15 s, and it matches `REQUEST_TIMEOUT` (`server.py:40`). The README
  states no page-poll interval; the code polls status every 3 s
  (`assets/app.js:372`) and the browser aborts a request after 20 s (`:54`) —
  neither is claimed, and the 5 s device-list refresh, 8 s discovery timeout and
  30 s scan interval exist only in the *uncommitted* text, not at `84411f8`.
- **Promised permissions and where enforced**: all enforced, at the lines in
  row 5 of the verified list.
- **Rollback the installer cannot do**: none found; the README's own limits
  (fixture restoration only, web component only, no power-loss durability,
  `:151-153`, `:188-189`) are accurate, and `install.py` performs no fsync for
  releases or units while the key path does (`server.py:462`), exactly as the
  README says.
- **Flags and files**: every flag named in the README exists (`--sink`,
  `--bind`, `--port`, `--host`, `--auth`, `--devices` at `install.py:156-163` and
  `server.py:552-562`), and every path in the table (`README.md:131-137`) is the
  path the code uses.

## Post-pin movement, outside this audit

`main` is now `9c9383d`, which adds `control/web/discovery.py`, extends
`PAYLOAD` to five files, and rewrites the README's discovery paragraph. Three
statements verified above become stale under that change and would need
re-checking, not re-asserting:

- `control/web/README.md:59-60` ("four fixed runtime files") — the working tree
  already says five;
- `docs/design/web-control.md:280-281` ("does not discover addresses") — mDNS
  discovery is being added;
- row 9 of the undocumented table (no polling number in the README) — the new
  text states 5 s / 8 s / 30 s, which must be compared with
  `server.py`'s `DISCOVERY_INTERVAL`/`DISCOVERY_TIMEOUT` and `app.js`'s
  intervals before it is trusted.

## Counts

**4 overclaims, 10 undocumented behaviours, 3 unclear items.** Sixteen verified
correct. Nothing was modified except this note; no server was started, no device
was contacted, and no audio path was touched.
