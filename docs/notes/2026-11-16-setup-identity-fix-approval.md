# Review record: the setup service's identity fix, approved at `823cba1`

**2026-11-16 — an independent review approved one tree.** This note exists so a
later session knows what was approved, on what evidence, and what it did not
cover. It cites the [first device run](../testing/results/2026-11-15-zero2w-setup-service-first-run.md)
rather than restating it.

Author: OpenCode session, `openrouter/deepseek/deepseek-v4.1-flash-1017`, variant
not exposed by the host. Reviewer: the `debra-review` subagent (independent
context, read-only, no shell). Review rounds: four, the last three rejecting the
candidate.

## What was approved

`823cba19b6188b5815b24de61c63781e3394418d` — "docs: stop claiming things the
device evidence disproves" — on top of
`99f065172cee967099307d2fb356ed7e312346a2` — "setup: apply the whole device name,
not only the hostname". The later commit changes four markdown files and no code,
so one approval covers both; the reviewer said so explicitly, preferring a single
approved tree to a code hash plus unreviewed prose.

The approved state is the code in `control/setup/nm.py` and
`control/setup/debra-setup.service`, the 25 identity tests, and the documentation
as it reads at that hash.

## What it fixes

`set_hostname()` renamed the device and stopped. Two other consumers of the name
kept the old one:

| Consumer | Symptom after a rename |
| --- | --- |
| `/etc/hosts` (`127.0.1.1`) | `hostname -f` → "Name or service not known"; every `sudo` → `unable to resolve host <new name>` |
| `avahi-daemon` | still answered `<old name>.local` |

Both were repaired only by the next boot, and `/etc/hosts` only because cloud-init
happens to rewrite it — so an image without cloud-init would keep the stale alias
indefinitely.

## What the review caught, and why it matters

Recorded because each one was a defect in the *fix*, not in the original code, and
the same mistakes are easy to repeat:

1. **A truncating write to a system file.** `open(path, "w")` is `O_TRUNC`; a kill
   between truncate and flush leaves `/etc/hosts` empty, and the retry path did
   not restore `127.0.0.1 localhost`, so the device would lose `localhost`. Now a
   staged file, fsync, `os.replace` on the resolved path, mode and owner copied,
   and `hosts_naming()` synthesises the localhost entry when it is missing.
2. **An ordering line that created a boot cycle.** The first draft ordered after
   `cloud-final.service`, which is itself `After=multi-user.target` — and this unit
   is `WantedBy=multi-user.target`. systemd would have dropped a job or an
   ordering edge. Now `cloud-init.service` and `cloud-init-network.service`, the
   stage that actually writes the file in both cloud-init eras.
3. **`restart` where `try-restart` was meant.** `systemctl restart` starts a
   responder somebody deliberately stopped. Now `is-active` then `try-restart`.
4. **A heuristic pretending to be a staleness test.** Comparing
   `hostnamectl --static` before and after answers "did Debra change the name",
   not "is the responder stale", and leaves a device stale when another tool did
   the rename. Removed; the responder is reconciled on every run.
5. **`UnicodeDecodeError` escaping a `except OSError`.** A non-UTF-8 byte in a
   comment would have crashed the unit at boot, defeating the "non-fatal" design.
   Both directions now use `surrogateescape`.
6. **A test that could not fail.** The "alias written after the rename" test
   compared two recorded commands; the alias write records no command, so moving
   it before the rename left the test green. It now snapshots the file at the
   moment the rename is issued.

## Device evidence

Release `b72a508c4eb98be4c713213761fe3a70047017d42bb9c55c8646638f2117279d` —
the id computed from the committed tree, so the board cannot have been running a
stray edit:

- `systemd-analyze verify` on the installed unit: no output, exit 0.
- Reboot: **0** ordering cycles; `cloud-init-network` finished at 18.17 s, the
  unit started at 24.31 s, `Result=success`, `NRestarts=0`.
- A forced live rename and its revert: alias, `hostname -f`, `sudo` and mDNS each
  followed within a second, Wi-Fi and the SSH session untouched.

## What the approval does not cover

Stated by the reviewer and worth keeping: no radio, no access point, no setup page
served to a phone, no join performed by Debra, no baseline restore (nothing
restores), no rename by a *first* boot, no rename during a join. The **atomic
replace and the unconditional reconcile have not run on a board** — the board
verified the behaviour with the earlier in-place, conditional mechanism. Nothing
here says anything about `control/web/` or the rest of the repository.

A later commit voids it: the approval names `823cba1` exactly.

## Reproducing the offline half

```sh
python3 -B -m unittest tests.test_setup_identity -v
python3 -B -m unittest discover -s tests          # 686 tests, 44 skipped
```
