---
title: A development bypass for the setup network, and a real password otherwise
date: 2026-11-15
type: project-learning
status: unreviewed
task: N02 (setup-r2 finding F02)
author: OpenCode agent, interactive session
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown (host reported no variant)
sources:
  - User statement, 2026-11-15, in this session
  - .local/reviews/setup-r2-20261115/verdict.md, finding F02 (read only)
  - control/setup/onboarding.py, control/setup/nm.py, control/setup/install.py (this change)
supersedes: []
---

## User requirement

Asked what to work on after the `setup-r2` review, James chose F02 (the setup
network's password) and added a constraint that changes the design:

> "we want easy development, so authentication bypass and the like are HIGHLY
> wanted for our development phase"

So the setup network must not be protected by anything a developer has to fetch
and type on every boot. That is a product decision, taken now, for this phase.

## What the review found (F02)

`hotspot_password()` returned `"debra-" + sha256(hostname)[:8]`. The access point
is named after the hostname (`Debra-Setup-345678`), so anyone in range could
compute the password from the broadcast name; hashing public information does not
make it secret. The same value was also returned in `/api/status`, and `nmcli`
was left to choose the access point's security (the manual allows a WEP
fallback).

## What is now implemented

Two modes, chosen at install time, never inferred:

- `--setup-security wpa` (**default**, `install.py` and the unit): a random
  12-character password from `secrets.choice` over an alphabet without
  0/O/1/l/I, kept in `/var/lib/debra/setup/setup-secret` (`0600`) so a re-raised
  access point still matches a note already read, written to the boot-partition
  note, and never served by the status API. The access point's
  `802-11-wireless-security.key-mgmt` is read back after it is raised; anything
  other than `wpa-psk` (in this mode) removes it and reports a failure.
- `--setup-security none`: the development bypass. The access point comes up
  open, the card note says "none (development build)", and the page says
  "This is a development build: the setup network has no password." The
  installer warns, and the unit records the choice as an argument, so an open
  network is always something someone wrote down.
- `control/setup/devserver.py` (the local, fake-NetworkManager server) defaults
  to `none`, because that is the path a developer clicks through; `wpa` is one
  flag away for exercising the real first-boot path.

An unknown mode is refused at both boundaries (`ValueError`), so a typo such as
`off` cannot be read as "open".

## Evidence

Executed in the worktree, offline, on this machine:

```sh
python3 -B -m unittest discover -s tests                  # 415 tests, OK, 20 skipped
DEBRA_BROWSER_TEST=1 python3 -B -m unittest tests.test_setup_browser -v   # 9 tests, OK
```

Four scratch mutations, each caught by the named tests (exit 1, i.e. the suite
failed as it should): default `security="none"`; skipping the key-management
read-back; returning the password in `/api/status`; deriving the password from
the device name again.

Incidental finding, fixed in the same worktree: `tests/test_docs.py` skipped any
page whose *absolute* path contained a `.local` part. A checkout under
`~/.local/share` therefore ran the image check over zero pages. It now tests the
path relative to the repository, so the check either runs or fails loudly (it
already asserted `checked > 0`).

## Not established

- No radio, phone or device was touched; nothing here has run on hardware.
- The mode is a per-install choice, not a per-boot one. A device installed with
  `none` stays open until it is reinstalled, by design.
- There is no timeout on the access point in either mode. "Bounded exposure" from
  the review is still only "the page stops when online".
- The password is handed to `nmcli device wifi hotspot` in its argument list, so
  another local user could read it from `/proc` while the access point is being
  created. That is unchanged from before this work, and a device in first-boot
  setup has no other users; it is named here rather than fixed.
- The `setup-r2` review's other findings (F01, F03–F14) are a separate repair and
  are not addressed here.
- Whether a shipped image should ever allow `--setup-security none` is a release
  question; nothing in this change enforces the answer.
