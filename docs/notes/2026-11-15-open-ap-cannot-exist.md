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
  - docs/notes/2026-11-15-dev-setup-bypass.md (the mechanism, not the intent)
---

This corrects [the earlier note](2026-11-15-dev-setup-bypass.md), which says the
open setup network "comes up open" and that the password is "handed to
`nmcli device wifi hotspot` in its argument list". Neither was true. The note is
left as written; this one supersedes those claims and cites them.

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

## Evidence

Executed in the worktree, offline, on this machine:

```sh
python3 -B -m unittest discover -s tests                                  # 547 tests, OK, 30 skipped
DEBRA_BROWSER_TEST=1 python3 -B -m unittest discover -s tests -p 'test_setup*.py'   # 47 tests, OK
```

Mutation evidence, each in a scratch copy under `/tmp/opencode` and reverted
there: re-delegating the access point to `nmcli device wifi hotspot` (5 failures
+ 3 errors in `AccessPointCheckTests`); ignoring the stored mode (3 failures);
dropping the page's poll guard over the change handover (1 browser failure);
disabling the key-management comparison (3 failures, re-run by the coordinator).

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
