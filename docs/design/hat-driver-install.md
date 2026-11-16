# Installing an audio HAT's driver: what "Install" could mean

Status: **proposal, unreviewed, no code written.** Written 2026-11-16 while
adding the board choice to the Setup card. It records the options for the one
action the page cannot currently perform, so the decision is about a shape
rather than a surprise later.

## The question

The Setup card now records which audio board a person says is fitted
([web control](../../control/web/README.md)). It deliberately does not install
anything: the button that would do it is a **Planned** sentence. This note is
about what that button would have to be, and why the web server must not be the
thing that does it.

## What installing actually is on this device

From the [Zero 2 W HAT result](../testing/results/2026-11-16-zero2w-web-portal-and-hat-audio.md),
installing the WM8960 board took three privileged steps and a reboot:

1. the overlay file `wm8960-soundcard.dtbo` present in `/boot/firmware/overlays/`,
2. a `dtoverlay=wm8960-soundcard` line in `/boot/firmware/config.txt`,
3. a reboot, after which `/proc/asound/cards` listed `wm8960soundcard` and the
   in-tree `snd-soc-wm8960` module bound it.

That is a boot-configuration change on a device that may be headless, several
metres from the person clicking. Two consequences shape everything below: a
mistake is not a failed request, it is a device that may not come back; and the
result cannot be observed until after a reboot, so "installed" is a claim the
page can only make later.

## Three routes

| Route | What the person does | Privilege | Honest button? |
| --- | --- | --- | --- |
| A. Record only (today) | says which board; installs by hand over SSH | none | no — it is a note, and the page says so |
| B. Show the exact command | copies one line the page prints, runs it over SSH | their own shell | not a button, but nothing is hidden |
| C. Privileged helper | presses **Install** | a root helper outside the server | yes, if the helper is narrow |

### A. Record only

Already implemented. The value is that the choice is kept, so a later route can
act on it, and the card can compare it with what the device reports. It does not
help the beginner who was promised no Linux.

### B. Print the command

The server composes a short script for the chosen board — overlay name, the
config line, a copy of `config.txt` beside it — and the page shows it with a copy
button. The person runs it over SSH or in the maintenance TUI, and the page
verifies afterwards by watching `/proc/asound/cards` and the running release.

This is deterministic and needs no new privilege boundary. It keeps the promise
"the page never has root" and still tells a person exactly what to type. Its
cost is that it is not the appliance experience: it is an instruction, and it
only works for someone who can already open a shell.

### C. A narrow privileged helper

A separate, root-owned unit — socket-activated, or a fixed `systemd` oneshot —
that accepts exactly one verb and one board id, both validated against the same
list the page uses. The server asks the helper; the helper writes `config.txt`
with a timestamped backup, refuses anything it was not told about, and never
reboots by itself. The page then reports what happened and waits for the reboot
before saying anything about the driver.

What this costs:

- a second privilege boundary to review, on a device that is already
  network-reachable and, on a keyless install, unauthenticated;
- the board matrix (roadmap A02) has to exist first, because the helper's list is
  only as good as the evidence behind each overlay name;
- a rollback path that restores `config.txt` from the backup, which is a boot
  action and therefore has to be proven on a device, not in a test;
- a reboot that a person has to agree to: the page cannot silently restart the
  device it is being read on.

## What must be proven before any of this (A02)

- the overlay name and kernel module for each supported board, per board revision;
- whether the codec binds without regulator control (the WM8960 case did, with
  dummy regulators, and that is not the same as a correct board profile);
- boot without an interactive login, with the overlay applied;
- a rollback that restores a working `config.txt` from the backup on a device
  that has already failed to boot once.

## Recommendation

Route **B** first: it is honest, needs no new privilege, and is useful to the
person who is already comfortable in a shell. Route **C** only after A02, and
only with the helper's verb list and validation reviewed as its own change — not
as a feature of the web server. Until then the card keeps the **Planned** row,
which is what it has now.

## Open questions for James

1. Is a copyable command worth having on the page, or is that a distraction from
   the appliance goal?
2. If the helper is wanted, is a socket-activated root unit acceptable on a
   household device, or should installation stay a maintenance-TUI action?
3. Should the page ever be allowed to ask for a reboot, or should that always be
   a separate, deliberate step?
