---
title: Merging the setup-secret branch into a moved main, and why the state schema is now 3
date: 2026-11-15
type: project-learning
status: unreviewed
task: N02 (setup-r2 finding F02) — integration and reconciliation
author: OpenCode agent, interactive session
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown (host reported no variant)
sources:
  - branch `setup-ap-secret`, approved candidate `c0a9bcd` (fifth review, approve)
  - branch `main` at `4c2edd1` (15 commits past the branch's base `5c9cf12`)
  - docs/notes/2026-11-15-open-ap-cannot-exist.md (the design this branch implements)
supersedes: []
---

This records the reconciliation, not a new design. The approved candidate is
unchanged in intent; the merged tree needs its own review, because the merge
changed it.

## Summary

`main` had moved under the approved branch and had independently defined its own
incompatible `SCHEMA = 2` — one that keeps the setup password inside
`setup.json` and adds a `revision` the page orders answers by. The branch, which
takes that password out of the record, also called its record schema 2. A naive
merge of the two would have produced a validator that either refuses every
upgraded device's state file or silently keeps serving the password.

The branch is now `SCHEMA = 3` and migrates both 1→3 and 2→3. `main` is merged
*into* the branch; the branch itself has not been pushed and `main` has not been
moved.

## Claims and evidence

| Kind | Claim | Source / date / scope | Verification and limits |
| --- | --- | --- | --- |
| observed | Two branches each claimed schema number 2 with different contents | `git show main:control/setup/state.py` vs the branch's `state.py`, 2026-11-15 | Read directly; `main`'s version has `hotspot_password` in `blank()` and a `revision`; the branch's has neither |
| observed | A schema-1 record describes an access point that cannot be joined, and is dropped | `state.read` on a schema-1 file, 2026-11-15 | Phase becomes `failed` and the retired key leaves the file; exercised on disk, not only in tests |
| observed | A schema-2 record keeps its described access point and loses its password | `state.read` on a schema-2 file, 2026-11-15 | The password is gone from the file on disk, not merely from the returned dict |
| proposed-decision | The access point is recorded *before* it is raised, and the record is corrected if the raise fails | `main`'s ordering, adopted into `start_hotspot` | A failed state write no longer leaves a live access point that nothing describes; a failed raise still clears the description |
| proposed-decision | `_fail` settles and re-raises under the admission lock | `main`'s change, kept | The lock had to become an `RLock` for this; the branch's password/mode state came along unchanged |
| open-question | Whether a phone joins a `wpa-psk` access point raised from this profile | unchanged from the earlier note | Still not run on a radio |

## Verification

- Working directory: the branch worktree; `python3 -B -m unittest discover -s tests`
  — 687 tests, 47 skipped, OK (231 onboarding, 40 installer cases in the files).
- `DEBRA_BROWSER_TEST=1 python3 -B -m unittest discover -s tests -p 'test_*browser.py'`
  — 47 tests, OK, against an installed Chromium.
- Devserver smoke, 2026-11-15: `GET /api/status` reports `security: none` and no
  password; `POST /api/security {"mode":"wpa"}` answers `202` with a 12-character
  password, writes `setup-secret` and `setup-security` `0600`, rewrites the card
  note with the same password, and a second POST within the interval answers
  `409`; `/api/status` then reports `wpa` with no password. Switching back to
  `none` rewrites the note to say the network is open. No radio was involved:
  the devserver's NetworkManager is the double.
- Schema migration checked on disk for schema 1 and schema 2, as above.
- Not tested: any real NetworkManager, a phone, or a reboot.

## What the merge changed in the branch, and what it did not

- Kept from the branch: the password in its own `0600` file, absent from
  `/api/status`, the page's mode toggle, the `202`-before-the-radio rule, and
  the cleartext limit documented in the earlier note.
- Kept from `main`: the `revision` counter and the page's ordering of answers by
  it, the handler-wide failure boundary on GET and POST with a released
  reservation, the handler's `_json_body` framing shared by both POST paths, the
  baseline failure remembered in memory, the attempt claim cleared on boot, the
  migration filling every field an older record did not write, and the
  `--enable` install path that accepts the absolute link `systemctl` writes.
- Removed: `hotspot_password` from the state and from every preset fixture, and
  `main`'s tests that asserted the password travels with the state.
