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
| observed | That password is moved to `setup-secret` and `wpa` to `setup-security` *before* the record is read | `adopt_legacy_secret`, called from `Onboarder.__init__`; `LegacySecretAdoptionTests`, 2026-11-15 | Without it, an upgrade opened a previously protected network, because the installed default is `none`. Tested offline; a second boot (schema 3) adopts nothing and stays `wpa` |
| proposed-decision | Only a schema-2 record that *carried a password* is adopted | same, tested by `test_a_record_without_a_password_is_not_an_upgrade` | The previous build wrote a password whenever it raised the access point, so no password means none was ever raised: nothing was protected, and the installer's flag still applies. A stored choice would outrank that flag for ever, so annotating a device nobody protected would freeze a decision nobody made |
| proposed-decision | The access point is recorded *before* it is raised, and the record is corrected if the raise fails | `main`'s ordering, adopted into `start_hotspot` | A failed state write no longer leaves a live access point that nothing describes; a failed raise still clears the description |
| proposed-decision | `_fail` settles and re-raises under the admission lock | `main`'s change, kept | The lock had to become an `RLock` for this; the branch's password/mode state came along unchanged |
| open-question | Whether a phone joins a `wpa-psk` access point raised from this profile | unchanged from the earlier note | Still not run on a radio |

## Verification

- Working directory: the branch worktree; `python3 -B -m unittest discover -s tests`
  — 788 tests, 50 skipped, OK (266 onboarding, 46 setup-installer, 25 identity cases
    in the files).
- `DEBRA_BROWSER_TEST=1 python3 -B -m unittest discover -s tests -p 'test_*browser.py'`
  — 50 tests, OK, against an installed Chromium (27 setup, 23 web).
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
  baseline failure remembered in memory, the attempt claim cleared on boot, and
  the `--enable` install path that accepts the absolute link `systemctl` writes.
- Narrowed from `main`: its migration filled *every* key an older record lacked
  from `blank()`, which turned a record with no `phase` into a fresh
  `unconfigured` device and wrote that back. Only the keys an earlier build
  could genuinely lack are filled now (`state.FILLED`); a record missing a core
  key is refused, as `read()` promises.
- Added after review: `connecting` with no token, `hotspot` with no described
  network and `online` with one are normalised to a usable record instead of
  stopping the service before an access point is raised.
- Removed: `hotspot_password` from the state and from every preset fixture, and
  `main`'s tests that asserted the password travels with the state.

## Corrections to the earlier note

`docs/notes/2026-11-15-open-ap-cannot-exist.md` is left as written. These are
the details in it that this work superseded; cite this note rather than that one
for them:

- It says `state.py` "is now schema 2" and that `read()` migrates by dropping the
  retired key and "filling anything the older schema lacked". Both are now wrong:
  the schema is 3, and only the fields an earlier build could lack are filled.
- It says the removed password is simply dropped. It is now carried into
  `setup-secret` and `wpa` into `setup-security` first, so the first boot after
  an upgrade cannot open a network that was protected. Two writes can still fail:
  a password that cannot be moved is replaced by a fresh one, and a mode that
  cannot be stored protects only that boot (see the residuals).
- It says the page reports "the mode the device is really in". It reports the
  mode the device has **stored**, which is what it will use on its next start;
  it is not re-derived from the running access point, so a change whose re-raise
  failed is reported as the new mode while the old network is still up.
- Its evidence block reports 621 tests (40 skipped) and 40 browser tests, and its
  prose says "three independent reviews". The counts are from before the merges
  with `main`; the numbers above are the current ones, and the review series is
  recorded in the work queue.

## What the tenth review caught in this note's own tree

The tenth review (`verdict-tenth.md`) returned **changes requested** for a defect
the merges created, not for the design: resolving `state.py` and the test file
against `main`'s line had left
`test_a_hotspot_phase_with_no_described_network_is_resolved` as a write with no
assertions, so deleting the `phase="hotspot"` with no described hotspot
normalisation failed no test. That normalisation is the only thing standing
between such a record and `validate`, which refuses it and stops the service
before any access point is raised. The read and three assertions are restored.

The same round settled `updated`, which was in both `state.FILLED` and
`state.MANDATORY_1`. It is mandatory — the first prototype revision (`cd4790f`)
already wrote it — so it is out of `FILLED` and two tests pin the refusal and the
ordinary fill of `revision`.

Three documentation claims in `control/setup/README.md` were false against the
code and are corrected: the migration is 1→3 **and** 2→3 rather than "from
schema 1"; it fills the five fields a later revision added and refuses a missing
core key, rather than "filling every field the old record never wrote"; and the
previous unit is snapshot to `previous-units/<stamp>.service`, not
`debra-setup.service.previous-<stamp>`. The installer was also said to install
"a random per-device password on the boot-partition note"; it writes the mode and
the service generates the password and the note at first boot.

## The device run this tree now carries, and what it does not transfer

`main` landed the first device run of the setup service
([result](../testing/results/2026-11-15-zero2w-setup-service-first-run.md), tree
`a90cfba`). It is evidence about this tree in places and not in others, and the
distinction is not obvious from the file, so:

- **Transfers:** the rename that worked, and the two defects it left
  (`/etc/hosts` and `avahi-daemon` keeping the old name), described this tree
  exactly when they were found. The same result then rebooted the board and
  measured both repairing themselves at boot, one of them because cloud-init
  rewrote `/etc/hosts` - a property of that image, not of Debra, which is why
  the window that matters is a rename on a running device. That window is now
  closed: main's `99f0651` makes `Nmcli.set_hostname` rewrite the alias and
  restart the responder as part of applying a name, and the merged tree carries
  it with `tests/test_setup_identity.py`.
- **Does not transfer:** that tree had no `NEVER_CAPTURE`, so its baseline
  archived `setup.json`. This tree excludes the whole state directory and the
  access-point profile, which is the safer behaviour and has only ever run
  against a temporary root. Its 9449-byte archive is therefore not evidence about
  this tree's exclusion list.
- **Out of scope for it entirely:** the setup access point, the page, a join
  performed by Debra and a restore. The unit has run both ways, a manual start
  and a boot, and both decided online and left the state alone.

## Residuals this work does not close

- **A rename applied by the fixed code has not run on a device.** The board
  verified the *behaviour* with an earlier draft that wrote `/etc/hosts` in
  place and restarted the responder only on a change; the atomic replace and the
  unconditional reconcile that `set_hostname` now does are covered offline only
  (`tests/test_setup_identity.py`). A rename by a *first* boot is also still
  unexercised.

- **An unreadable mode file fails open when the installed default is `none`.**
  `_stored_security()` logs and returns "no choice", so a device whose page chose
  `wpa` but whose `setup-security` cannot be read comes up in the installed
  mode. Reading the file is a permission and corruption question, not a mode
  question, and failing closed would strand a device that was never protected.
  Not changed.
- **The card note is written non-atomically.** A power cut while it is being
  rewritten can truncate it; the next raise rewrites it, and the password
  itself is in `setup-secret`, so the loss is the note rather than the
  credential. Not changed.
- **`status.security` is the stored mode, not the running access point's.** It
  is set at construction and by a change, and never re-derived from what is
  actually up. When a stored change's re-raise fails, the page reports the mode
  the device will use on its next start, not the one it is serving. That is the
  useful answer for the person, and it is not the same claim; the page copy and
  this note now say "the mode the device will use".
- **A mode that cannot be stored protects only this boot.** If the mode file
  cannot be written during an upgrade, the adopted `wpa` is used for the running
  process (so the access point is protected now) but the next boot falls back to
  the installer's flag. The journal says so. Nothing can be persisted on that
  filesystem, so this is the strongest available outcome, not an oversight.
