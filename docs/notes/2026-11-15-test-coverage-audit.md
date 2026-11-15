---
title: Mutation audit of web control, discovery, activity and model tests
date: 2026-11-15
type: project-learning
status: unreviewed
task: test-coverage-audit
author: OpenCode subagent
author_model: openrouter/openai/gpt-6.1-terra
author_variant: unknown
sources: ["Debra commit 84411f8d4ec5c2b227add0823bf816dbd70234d2", "isolated host-only mutation runs, 2026-11-15"]
supersedes: []
---

## Scope and method

Observed at the requested commit, **not** the uncommitted working-tree changes. Each mutant below changed one behavior in its own copy under `/tmp/opencode/cov-audit/experiments/`; the complete default suite was run for each. `G` means 161 tests green, 12 browser tests skipped; `F` means the named test failed. Mutation scripts/logs remain there or in `/tmp/opencode/cov-*.log`. `W`, `B`, `D`, `A` mean `tests/test_web.py`, `tests/test_web_browser.py`, `tests/test_discover.py`, `tests/test_activity.py`, respectively. Line numbers refer to the commit. Fakes handle audio and process calls; HTTP uses loopback. No device was contacted.

These are **specific mutation results**, not proof that every alternative break is detected. At this commit `/api/devices` serves only configured records (`control/web/server.py:404`); `tools/discover.py` is a separate CLI, with no call from the page/server. There is no first-scan cache/window to mutate here. `bad-.local` is accepted by the standalone parser but rejected by `canonical_device_url`; this does not establish that an announcement can reach the page. The later uncommitted discovery implementation is outside this audit.

## Behavior

| Behaviour (file:line) | Nearest test | Would it fail if broken? | Evidence (the mutation and the result) |
| --- | --- | --- | --- |
| `control/web/server.py:390` wrong bearer on audio POST | W:278 checks status, not POST | No | `auth_audio_wrong`: permit wrong key on audio only; G. Synthetic wrong-key volume POST returned 200 and changed fake volume to 20. |
| `control/web/server.py:392` missing bearer on audio POST | W:278 checks status, not POST | No | `auth_audio_missing_really`: permit absent key on audio only; G. Synthetic missing-key mute POST returned 200 and changed fake mute. |
| `control/web/server.py:393` wrong key on status | W:278 | Yes | `auth_wrong`: bypass comparison globally; F. |
| `control/web/server.py:390` explicit no-key mode works | W:486, 492 | Yes | `noauth_block`: return 401 for keyless mode; F. |
| `control/web/server.py:375` Host allowlist and duplicates | W:296, 332 | Yes | `host`: bypass Host check; F. |
| `control/web/server.py:379` cross-site refusal | W:296 | Yes | `cross_site`: bypass check; F. |
| `control/web/server.py:382` write Origin refusal | W:301 | Yes | `origin_write`: bypass Origin equality; F. |
| `control/web/server.py:424` transfer encoding rejection | W:347 | Yes | `content_length`: ignore Transfer-Encoding; F. |
| `control/web/server.py:213` volume range | W:96, 313 | Yes | `invalid_volume`: accept -1 and 101; F. |
| `control/web/server.py:215` selected native sink | W:88 | Yes | `wrong_sink`: use default alias for volume; F. |
| `control/web/server.py:224` missing sink prevents write | W:109, 321 | Yes | `no_sink`: skip availability probe; F. |
| `control/web/server.py:285` status cannot restart services | W:81, 263 | No | `status_restart`: add fake `systemctl --user restart sendspin.service` on uncached status; G. |
| `control/web/server.py:289` fresh audio despite status cache | W:132 | Yes | `cached_audio`: return cached audio; F. |
| `control/web/server.py:187` queued write deadline | W:197 | Yes | `lock_deadline`: wait one second regardless of deadline; F. |
| `control/web/server.py:40` request/command timeout ceilings | W:216, 369 | No | `request_timeout`: 15→900 s; `command_timeout`: 2→600 s; each G. Tests override the former or compare against the latter. |
| `control/web/server.py:65` subprocess nonzero exit | W:126 | No | `run_returncode`: ignore nonzero exit; G. Audio failure test replaces the runner rather than exercising `run_command`. |
| `control/web/assets/app.js:302` preview does not change volume | B:605 | Default no; opt-in yes | `ui_auto_apply`: POST on slider input; G. Opt-in Chromium: F, `slider preview wrote audio`. |
| `control/web/assets/app.js:360` keyless probe only on explicit `auth=none` | B:574 | Default no; opt-in yes | `ui_bypass`: trust any HTTP 200; G. Opt-in Chromium: two probe tests F. |
| `control/web/assets/app.js:309` reject credential-bearing device URLs | B:595 | Default no; opt-in yes | `ui_url`: allow URLs containing `@`; G. Opt-in Chromium URL-contract test F. |
| `control/web/assets/app.js:54,326,358` fetch timeouts | B:580, 605 | No, even opt-in | `ui_timeout`: all three deadlines 20→2,000 seconds; G, and the full opt-in suite also passed. Synthetic fetch does not honor the abort signal. |
| `control/web/server.py:462` key staging flush to disk | W:591 | No | `key_fsync`: remove `fsync`; G. A call assertion alone would not prove crash durability. |
| `control/web/server.py:450,473` state owner check | W:649 | No | `owner_check`: remove owner checks; G. Test covers mode, not wrong owner. |
| `control/web/server.py:475` key symlink rejection | W:635 | Yes | `key_symlink`: remove `O_NOFOLLOW`; F. |
| `control/web/install.py:110` release file permissions | W:655 | No | `payload_mode`: 0600→0644; G. Parent privacy is a separate protection. |
| `control/web/install.py:148` service unit permissions | W:655 | No | `unit_mode`: 0600→0644; G. |
| `control/web/install.py:98` existing release integrity | W:655 | No | `payload_integrity`: stop comparing release bytes; G; no tampered-release fixture. |
| `control/web/install.py:77` copied payload contents | W:655 | No | `payload_wrong`: replace installed app with broken bytes before hashing; G. Filenames/idempotence are checked, not source-byte equality. |
| `control/web/install.py:46` full list content address | W:749 | No | `dev_hash`: truncate SHA-256 to eight hex digits; G. Existing byte verification still rejects a collision. |
| `control/web/install.py:62` private list mode | W:737, 769 | Yes | `dev_mode`: fchmod 0644; F. |
| `control/web/install.py:140` prior unit backup bytes | W:667, 708, 749 | Yes | `backup`: write wrong backup bytes; F, including interrupted replacement. Fixture restore is not device recovery. |
| `tools/discover.py:70` service filter | D:43 | Yes | `discover_service`: accept other service types; F. |
| `tools/discover.py:90` URL filter | D:43 | No | `discover_url`: remove URL filter; G. Synthetic `evil@safe.local` then yields `http://evil@safe.local:8787/`; no page integration exists here. |
| `tools/discover.py:113` device-list adapter | D:61 | No | `discover_device_list`: always return `[]`; G. |
| `tools/discover.py:39` escaped-semicolon handling | D:23 | No | `discover_escape`: stop recognizing backslashes; G. |
| `tools/discover.py:26` browse deadline | D:90 | No | `discover_timeout`: 8→900 s; G. Timeout exception reporting itself is separately exercised. |
| `tools/activity.py:47` session command deadline | A:176 | No | `activity_timeout`: 15→900 s; G. |
| `tools/activity.py:322` loopback port probe | A:106 | No | `activity_port`: probe `port+1`; G; render tests mock `web_snapshot`. |
| `tools/activity.py:514` atomic snapshot replacement | A:116 | No | `activity_atomic`: write directly to final file; G. |
| `tools/activity.py:534` no-color on terminals | A:391 | No | `activity_color`: ignore flag; G; captured stdout is not a TTY. |
| `tools/activity.py:204` all session rows | A:305 | No | `activity_drop_middle`: render only first and last of 40; G. |
| `models/parts/dweii-462-retainer/build-script.json:10` screw-hole diameter | no geometry test | No | `model_holes`: 2.8→0.1 mm; G. Docs tests check links/assets, not model build geometry. |

## Vacuous assertions / skipped coverage

The following assertions are vacuous **for the named property**; most enclosing tests can still fail for other reasons. They are not claimed to pass under every imaginable change. Each listed mutant left the complete default suite G.

| Vacuous test (file:line) | Why it cannot fail | The mutation that left it green |
| --- | --- | --- |
| `tests/test_discover.py:61` | Constructs the three keys itself instead of calling the adapter; cannot check adapter output. | `discover_device_list` returns `[]`. |
| `tests/test_discover.py:90` | Timeout assertion compares to the same mutable production constant, not a fixed bound. | `discover_timeout` uses 900 s. |
| `tests/test_activity.py:176` | Timeout assertion compares to production's own constant. | `activity_timeout` uses 900 s. |
| `tests/test_activity.py:116` | Checking final text and absence of a temp file cannot distinguish an atomic replace from direct writing. | `activity_atomic` writes final file directly. |
| `tests/test_activity.py:391` | Captured stdout is non-TTY, so the flag cannot affect the color decision. | `activity_color` ignores `--no-color`. |
| `tests/test_activity.py:305` | Checks only `s39`, `s0`, and absence of `hidden`, not the other 38 rows. | `activity_drop_middle` omits those rows. |
| `tests/test_web.py:81` | Only searches calls for `set-sink`; cannot detect a service restart. | `status_restart` adds one to the fake runner. |
| `tests/test_web.py:655` | Asserts filenames and self-consistency, not installed bytes or file/unit modes. | `payload_wrong`, `payload_mode`, `unit_mode`, each separately G. |
| `tests/test_web_browser.py:35,580` | The synthetic fetch does not honor `AbortSignal`; tests cannot detect an excessive request deadline. | `ui_timeout` 20→2,000 seconds; both complete suites green. |
| `tests/test_web_browser.py:498` | All 12 tests are skipped in the default run, though the skip is reported; they are not intrinsically vacuous. | `ui_auto_apply` and `ui_bypass` G by default, both F with opt-in Chromium. |

## Five priorities for new or strengthened tests

1. In key mode, send missing and wrong Authorization to **both** audio POSTs; require 401 and zero fake mutator calls, while valid keys still succeed.
2. Whitelist every command on status, startup, discovery and install; fail on fake `systemctl start/stop/restart` or native audio writes absent an explicit action.
3. Run the synthetic browser tests in an explicit regular test job; catch slider-preview writes and false keyless bypass, while retaining opt-in for environments without Chromium.
4. Verify exact installed bytes, owner-only modes, full list hash, tampered-release refusal and interrupted rollback in disposable fixtures; add a separate crash/recovery plan rather than claiming power-loss proof.
5. Test hostile/escaped discovery records through every eventual discovery-to-page boundary and first-scan pending/cache/timeout states when that integration exists; independently enforce absolute timeout budgets.

## Verification and handoff

From `/tmp/opencode/cov-audit`: `python3 -B -m unittest discover -s tests` produced the following verbatim trailer:

```text
----------------------------------------------------------------------
Ran 161 tests in 7.485s

OK (skipped=12)
```

`DEBRA_BROWSER_TEST=1 python3 -B -m unittest discover -s tests` also passed all 161, including the synthetic Chromium tests. No live service, audio, installer deployment, physical model build, or power-loss recovery was tested. This note proposes tests only; it authorizes no deployment or device operation.
