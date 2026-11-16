---
title: The open setup network could not exist, and what replaced it
date: 2026-11-15
type: project-learning
status: unreviewed
task: N02 (setup-r2 finding F02) — correction to the bypass design
author: OpenCode agent, interactive session
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown (host reported no variant)
sources:
  - nmcli(1) 1.42.4 (Raspberry Pi OS Bookworm), https://manpages.debian.org/bookworm/network-manager/nmcli.1.en.html
  - NetworkManager NEWS 1.20 entry (a modified profile is inert until re-activation), tag 1.42.8
  - NetworkManager settings docs, 802-11-wireless-security and ipv4
  - src/core/nm-netns.c (nm_netns_shared_ip_reserve), tag 1.42.8
  - docs/notes/2026-11-15-dev-setup-bypass.md (superseded claim), read 2026-11-15
supersedes:
  - docs/notes/2026-11-15-dev-setup-bypass.md (the mechanism, the default, and
    the lifetime of the mode)
---

This corrects [the earlier note](2026-11-15-dev-setup-bypass.md). That note is
left as written; this one supersedes its claims and cites them, including four
that a later reviewer found still wrong:

- **Its line 41 says `wpa` is the default** ("`--setup-security wpa` (default,
  `install.py` and the unit)"). The default is `none`, as its own line 48 says
  and as `DEFAULT_SETUP_SECURITY` in `onboarding.py` implements. The installer
  writes whichever mode it was given into the unit, so the flag is explicit; the
  *default when the flag is omitted* is the open network.
- **Its lines 85-86 say the mode is per-install** ("A device installed with
  `none` stays open until it is reinstalled, by design"). It is not: the page
  stores the choice in `setup-security` and it survives reboots, which is what
  `POST /api/security` exists for.
- **Its line 93 says the review's other findings are not addressed.** All
  fourteen are addressed in this branch.
- **Its "Evidence" counts (415 tests, 9 browser cases) are stale.** The figures
  at the end of this note are the ones this work was checked against.

Its claims about the mechanism were also wrong, which is the section below.

## What was wrong

`Nmcli.start_hotspot()` called `nmcli device wifi hotspot …` and left `password`
off when there was none. `nmcli(1)` 1.42.4 says of that option:

> If not provided, nmcli will generate a password.

So the call never produced an open network. It produced a WPA2 one whose
password nmcli had invented and shown to nobody. The read-back check added in
the same change expected an empty key management for the open mode, would have
found `wpa-psk`, removed the access point, and raised `NmError`. With `none` as
the default, a real device would have come up with **no setup network at all**:
nothing to join, a card note describing a network that did not exist, and no
page. The repository's own deleted docstring had said this ("`nmcli` silently
generates a password nobody is ever shown"); the claim was dropped when the
first password was introduced and the behaviour it described was never
re-checked.

The offline double could not see it, because the double answered whatever it was
told. A fake is evidence about the code's decisions, never about the tool's
behaviour, and this code's correctness rests entirely on what `nmcli` does. This
is the second time in this work that the same shape of mistake appeared: the
first was a test double that reported success for a profile NetworkManager had
never loaded.

## What replaced it

The access point is now an explicit keyfile this code writes into
`PROFILES_DIR` (staged then renamed, `0600`, stable `uuid5`, `id=debra-setup`,
`wifi.mode=ap`, `interface-name`, `autoconnect=false`, `ipv4.method=shared`,
`ipv6.method=ignore`, and `wifi-sec.key-mgmt` of `wpa-psk` with a PSK or `none`
without one). Then `connection reload` → `connection down` if it is the device's
active connection → `connection up` → verify. The password never enters argv.

Three findings from the same research shaped it:

- **A reload or `connection modify` does not re-key a running access point.** The
  device keeps the settings it was activated with until the profile is fully
  re-activated (NetworkManager NEWS, 1.20), so the connection is cycled.
- **An open profile reports `key-mgmt` as `none`, not as an empty string.** The
  comparison that expected `""` would have failed even against a correct open
  profile.
- **`connection show id <name>` reports the profile, not the running access
  point.** Verification reads the profile's key management *and* `device show
  <if>` for `GENERAL.STATE` 100 and `GENERAL.CONNECTION=debra-setup`.

Keeping one profile rather than deleting and recreating it is deliberate: in
shared mode NetworkManager hands 10.42.0.1 to the first shared connection and
10.42.1.1 to the next (`nm_netns_shared_ip_reserve`), so a delete/recreate moves
the address the setup page is already bound to. The mode is rewritten into the
same profile and the same connection is cycled; the address is read again
afterwards and a move is recorded rather than ignored.

## What the mode switch adds

The mode is no longer only an install argument. `POST /api/security` accepts
`{"mode": "wpa"|"none"}`, stores the choice in `<state dir>/setup-security`
(`0600`, one word) beside `setup-secret` — not in `setup.json`, whose schema is
closed and would reject every existing state file — and answers **202 before the
radio changes**, as a join does. The password is returned in that one reply and
nowhere else: not in `/api/status`, not in the state, not in the journal. A reply
that cannot be delivered reverts the stored mode, because raising a network that
demands a password nobody was told is worse than not changing it.

## What the second review changed

The first independent review of this work returned fourteen findings. Answering
them produced five more that only appeared in the repair, and the worst of those
was a lockout:

- **One password, and it is the one the radio uses.** Making
  `hotspot_password()` the single reader was not enough while `setup_secret`
  still *generated* a different password on each call whenever it could not save
  one - a read-only or full state directory, or a file left empty by a power
  loss between creating and writing it. The reply could then carry one password
  and the access point demand another. `setup_secret` now repairs an empty file
  instead of treating "exists" as "has a password", and the value it could not
  save is held for the life of the process.
- **The radio is always given back.** `rearm_hotspot` clears its claim in a
  `finally`; the handler did not, so any failure between claiming the radio and
  starting the worker (an unreadable state file, a thread that could not be
  created) refused every join and every later change until the service
  restarted. The handler now releases the claim unless it handed it to a worker.
- **A failed change does not invent a stored choice.** Reverting wrote the mode
  that was already in force into `setup-security`. A stored file outranks the
  installer's flag for ever after, so a later `--setup-security wpa` would say
  `wpa` in the unit and the device would keep coming up open.
- **The other copy of the password is excluded too.** The access point's own
  NetworkManager profile holds it as `psk=` while the access point is up, and
  that directory is captured in full by every baseline. A power loss between
  raising and joining left the file for the next boot's baseline to archive.
- **An empty key-management value counts as open.** `none` is what a
  `key-mgmt=none` profile is documented to report, but a build that materialises
  no security setting prints nothing - and treating that as a mismatch would
  take down the only setup network the device has. Only the open mode accepts
  it; a password still demands `wpa-psk`.

## Evidence

Executed in the worktree, offline, on this machine:

```sh
python3 -B -m unittest discover -s tests                                 # 607 tests, OK, 39 skipped
DEBRA_BROWSER_TEST=1 python3 -B -m unittest discover -s tests -p 'test_*browser.py'  # 39 tests, OK
```

Mutation evidence, each applied in this checkout and reverted with `git
checkout` (or in a scratch copy under `/tmp/opencode`), so each is a defect the
suite is known to catch:

| Mutation | Result |
| --- | --- |
| Re-delegate the access point to `nmcli device wifi hotspot` | 5 failures + 3 errors in `AccessPointCheckTests` |
| Ignore the stored mode | 3 failures in `SetupSecuritySwitchTests` |
| Read the key management with `-t` instead of `-g` | `NmError: could not be secured as asked` in `AccessPointCheckTests` |
| Drop the page's poll guard over the change handover | 1 browser failure |
| Make the toggle's lost reply claim success | 1 browser failure |
| Drop the join/change reservation in `admit` | 1 failure (join refused during a change) |
| Drop the phase from "is there an access point" | 1 failure (change allowed during a join) |
| Remove the password cache in `hotspot_password` | 1 failure (reply and access point disagree) |
| Always write a mode file when a reply is lost | 1 failure (a choice nobody made) |
| Do not release the radio when the worker cannot start | 1 failure (joins refused for good) |
| Stamp the throttle only at the start of a change | 1 failure (a long change is immediately repeatable) |
| Do not record a rearm that cannot run | 1 error (uncaught `OSError` in the worker) |
| Accept only `none`, not an empty value, as open | 1 error (an open access point is torn down) |
| Stop excluding the setup state from a baseline | 1 failure (the password reached the archive) |

## Known limits of the mode switch

These are accepted for the development phase, and they are properties of the
current design rather than defects to be discovered later.

- **The password is served over cleartext HTTP.** `POST /api/security` is
  answered on port 80 of the setup access point, which has no transport
  security. Switching from the open mode therefore sends the new password over
  the open network, and anyone in range capturing that exchange has it. The
  password is stable (`setup_secret` reuses its file), so it stays valid on
  later boots. The reply is "the one place the password is served", but on an
  open access point that means anyone who has joined, not anyone who was
  invited. It protects what comes after the change, not the moment of it.
- **A lost reply is not the same as a lost change.** The device writes the mode
  and answers 202 before it touches the radio, so a reply that never arrives
  may mean the change started or may mean nothing happened. The page says it is
  not known yet rather than claiming either, and the next status poll reports
  the mode the device is really in.
- **An address that moves is recorded, not fixed.** The profile is rewritten in
  place to keep the shared-mode address stable, but if it moves anyway the
  listening socket does not follow it; the state records why and a service
  restart is still required.

## Not established

- **No radio, no NetworkManager and no `nmcli` ran.** The profile syntax, whether
  the keyfile plugin accepts `key-mgmt=none` for an AP, whether
  `reload`→`down`→`up` actually re-keys a live access point, whether
  `ipv4.method=shared` behaves as described, and whether `GENERAL.STATE` parses
  as `100` are all supported by the manual and a double, not by execution.
- Whether `connection reload` is needed when the file is replaced in place is
  unknown; it is kept as explicit and harmless.
- An address that moves is recorded and warned about, but the listening socket
  still needs a service restart to follow it. Unchanged from before.
- The mode file survives a reboot, so a device switched to `wpa` on the page
  stays protected across boots — by design, and untested on hardware.
