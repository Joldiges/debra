# Installing an audio HAT's driver: what "Install" could mean

Status: **route C implemented and tested offline; one round trip still needs a
device.** Written 2026-11-16 while adding the board choice to the Setup card,
and implemented the same day after James answered the open questions below: the
dashboard must be able to do the full set, and a narrow `sudo` step is
acceptable. What exists, what it refuses and what is still unproven are in
[the helper's README](../../control/setup/README.md#the-audio-hat-helper-hat_installpy)
and [the web README](../../control/web/README.md). This note is kept because the
comparison of the three routes is still the reasoning behind the shape, not
because the decision is still open.

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

## What was chosen

Route **C**, with a socket-activated unit, after James's answer on 2026-11-16:
the dashboard must be able to do the full set, and a selective elevated step is
acceptable. A `sudo` rule was implemented first and **abandoned on the device**:
the generated web unit ships `NoNewPrivileges=yes`, so a setuid `sudo` cannot
escalate from the service at all. The only way to make it work would be to delete
that line, which trades real hardening for one feature. The socket needs no
setuid binary and leaves the hardening in place.

The narrowest version of C is one root program started by one socket:

- the socket starts **one path with no arguments**, and the request is JSON on
  the connection, so nothing can use it to reach another command or argument;
- the board is validated inside the helper against `control/web/hats.py`, the
  same file the page reads, so there is one answer to "which overlay is this
  board";
- the server sends the **recorded** board id, never one from the request body, so
  a page cannot install something nobody chose;
- `config.txt` is copied first, written atomically, read back, and restored from
  the copy if the read-back is wrong;
- `reboot` is a separate verb and a separate button, and `install` never restarts.

The earlier objection to the socket — "two units, a protocol and a group to
review" — is real, but the alternative turned out not to exist: the sudo rule
works from a shell and cannot work from the service. A boundary that cannot be
used is not the simpler one. The group is the page's own account, so no new
account or membership has to be created.

Route B is not gone: the enrollment command is printed by the installer, and it
is the only step that needs a password.

## Open questions, answered

1. *Is a copyable command worth having?* Yes, for exactly one thing: the
   enrollment step. It is printed by the installer and shown on the card when the
   helper is not enrolled, because no page can do it for the person.
2. *Is a socket-activated root unit acceptable?* Yes — and it is what the device
   requires. The `sudo` rule was implemented, failed on the Pi 5 because of
   `NoNewPrivileges=yes`, and was replaced.
3. *Should the page ever ask for a reboot?* Yes, but only as its own deliberate
   step: a separate button, a browser confirmation, and a server that requires
   `{"confirm": "restart"}` before it sends anything. The helper never restarts
   on its own.

## What A02 still owes

- a measured install on a device for each supported board, and a boot that comes
  back with the card bound;
- the rollback proven on a device that has already failed to boot once;
- the ReSpeaker v2 codec-family question: the kernel's `respeaker-2mic-v2_0`
  overlay names `tlv320aic3x` while the v2 board carries a TLV320AIC3104;
- whether the Waveshare board's pinout really matches the overlay measured with
  a Seeed v1 board.
