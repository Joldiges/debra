# Installing an audio HAT from the dashboard, on the Pi 5

**2026-11-16 — the Setup card's Install button changed `/boot/firmware/config.txt`
on a real device, through a socket-activated root helper, and did not reboot.**
The write had only ever run offline; this is the first round trip that started
from the HTTP endpoint the page calls. The driver binding after a restart is
still unproven, and so is every board except the one already on this device.

Author: OpenCode session, `openrouter/deepseek/deepseek-v4.1-flash-1017`, variant
not exposed by the host. Board: Pi 5, `debra-3c6b3f`, `192.168.0.8`, kernel
`6.12.x` aarch64, ReSpeaker 2-Mics Pi HAT v2 on `respeaker-2mic-v2_0`. Two other
boards were read but not written (below).

## Why the transport changed during the work

A passwordless `sudo` rule was implemented first, and it worked from an SSH
shell: the helper ran, the file changed, the backups were made. It then failed
from the service, which is the only caller that matters:

```
$ cat ~/.config/systemd/user/debra-web.service
NoNewPrivileges=yes
```

`sudo` is setuid. `NoNewPrivileges=yes` is exactly the setting that stops a
setuid binary from granting privilege, so `sudo -n` cannot work from this unit at
all — as a shell, a scope, or the real service. The only way to make it work
would be to delete that line, which removes a real hardening measure from a
network-reachable service to gain one feature. That trade was refused.

The transport is now `debra-hat.socket` (`Accept=yes`, `SocketMode=0660`,
`SocketGroup=debra`) plus `debra-hat@.service` (`StandardInput=socket`,
`StandardOutput=socket`, `NoNewPrivileges=yes`, `PrivateTmp=yes`,
`ProtectHome=yes`). One connection starts one root process, it reads one JSON
request, answers, and exits. The web service keeps its hardening and there is no
passwordless `sudo` rule anywhere on the device.

## What was run

Enrolment, once, with a password:

```
$ sudo python3 -B /tmp/debra-hat-stage/control/setup/hat_install.py --enroll
{"ok": true, "changed": true,
 "installed": ["/usr/local/sbin/debra-hat-install",
               "/etc/systemd/system/debra-hat.socket",
               "/etc/systemd/system/debra-hat@.service"],
 "retired": ["/etc/sudoers.d/debra-hat"], ...}
```

The retired file is the rule the abandoned sudo version wrote on this device.
Enrolment removes it only when its first line is Debra's own marker.

```
$ ls -l /run/debra-hat/control.sock
srw-rw---- 1 root debra 0 Nov 16 13:05 /run/debra-hat/control.sock
$ systemctl is-active debra-hat.socket; systemctl is-enabled debra-hat.socket
active
enabled
```

The page's own endpoints, against the deployed release:

```
$ curl -s -H 'Host: debra-3c6b3f.local:8787' \
       -H 'Origin: http://debra-3c6b3f.local:8787' -H 'Content-Type: application/json' \
       -X POST --data '{"choice":"respeaker-2mic-hat-v1"}' http://127.0.0.1:8787/api/setup/hat
{"choice": "respeaker-2mic-hat-v1"}
$ ... --data '{}' .../api/setup/hat/install
{"ok": true, "changed": true, "config": "/boot/firmware/config.txt",
 "backup": "/boot/firmware/config.txt.debra-20261116-130532",
 "overlay": "wm8960-soundcard", "dropped": ["respeaker-2mic-v2_0"], ...}
$ tail -2 /boot/firmware/config.txt
[all]
dtoverlay=wm8960-soundcard
```

Choosing v2 again and pressing Install put the original line back (backup
`config.txt.debra-20261116-130532-2`, `dropped: ["wm8960-soundcard"]`). A body
that names a board is refused with `400` ("the recorded choice is used"), and a
restart without `{"confirm": "restart"}` is refused with `400`. `uptime` was
unchanged across all of it: 13 hours 8 minutes before and after.

The socket path was also exercised directly, without the server, as the `debra`
account:

```
$ printf '{"verb":"remove"}\n' | python3 -c '...connect("/run/debra-hat/control.sock")...'
{"ok": true, "changed": true, ..., "dropped": ["respeaker-2mic-v2_0"], ...}
```

## The file, and what the edit does not touch

Before and after the two writes, `diff` against the oldest backup
(`config.txt.debra-20261116-125532`) shows exactly one changed line:

```
6c6
< #dtparam=i2c_arm=on
---
> dtparam=i2c_arm=on
```

The graphics overlay, `dwc2`, `nospi10`, every comment and the `[pi5]` section
are byte-identical. The overlay line is restored exactly, not approximately. The
helper also appends `[all]` when the file ends inside a conditional section; this
file already ended with one, so nothing was added.

## All three boards enrolled, and two more written

Enrolment needs a password, so on the Zero 2 W and the Zero W it was run through
`sudo -S` with the lab password James authorised for these boards. On both it
wrote the same four files, reported `retired: []` (neither had ever had the
abandoned sudo rule), and left a socket at `/run/debra-hat/control.sock`,
`0660 root:debra`, `debra-hat.socket` `active`.

The preflight refusal is real, not theoretical. The Zero 2 W's 64-bit image has
`wm8960-soundcard.dtbo` but no `respeaker-2mic-v2_0.dtbo`, so the v2 row is
reported un-installable per board rather than failing after the write:

```
-- record v2 (an overlay this image does not carry):
{"choice": "respeaker-2mic-hat-v2"}
-- install, expecting a refusal:
{"error": "This image has no respeaker-2mic-v2_0 overlay, which is what ReSpeaker 2-Mics Pi HAT v2 needs. Nothing was changed."}
-- config tail after the refusal (must be unchanged):
dtoverlay=nospi10

[all]
```

The file ended at `[all]` with no overlay line, which is what it was before the
refusal: nothing was written. Recording the board that is actually fitted (v1)
and pressing Install then wrote `dtoverlay=wm8960-soundcard`.

The Zero W carries the overlay, so its v2 choice installed normally.

| Board | Helper socket | `respeaker-2mic-v2_0` on image | v2 row reports |
| --- | --- | --- | --- |
| `debra-3c6b3f` (Pi 5) | present | yes | installable |
| `debra-8518d6` (Zero 2 W) | present | **no** | *"This image does not carry the respeaker-2mic-v2_0 overlay."* |
| `debra-f943dc` (Zero W) | present | yes | installable |

**Each board's file was put back byte for byte.** Every write copies the file
*before* changing it, so the oldest backup on each board is its pre-test state.
After a full remove-then-install cycle on both Zeros, `diff` against that oldest
copy is empty on both — the managed line is restored at the same place, with the
same comments around it, not merely re-added somewhere. Two backups per board and
no more: one refusal wrote nothing, so it left nothing behind.

## The restart, pressed

The Restart button and the socket `reboot` verb had never been used. James
approved one interruption on the Pi 5, which is the lab voice satellite.

```
$ curl -X POST .../api/setup/restart --data '{"confirm":"restart"}'
{"ok": true, "rebooting": true, "note": "The device is restarting. The page will come back on its own."}
```

The helper logged `debra-hat-install reboot` and the transient unit exited;
`ssh` answered again after about 55 seconds and the web page came back on its
own. After the boot:

| Check | Result |
| --- | --- |
| `uptime -p` | `up 0 minutes` — it really restarted |
| `/proc/asound/cards` | `0 [seeed2micvoicec]` — the v2 driver bound again |
| `config.txt` tail | `[all]` / `dtoverlay=respeaker-2mic-v2_0` — the line survived the boot |
| `/run/debra-hat/control.sock` | recreated, `0660 root:debra` |
| `debra-hat.socket` | `active` (it is `enabled`, so it returns without a login) |
| `debra-web.service` | `active` |

So one full loop is closed: the page wrote the line, the line survived a restart,
and the driver it names bound on the other side. That is the Pi 5 with the board
it already had. It says nothing about a *different* board on the same device.

## The card, in a real browser

The page was loaded from the device in headless Chrome over the DevTools
protocol, with the keyless device's own "continue without a key" button pressed
and the Setup disclosure opened. Nothing was guessed: the report is the page's
own DOM.

| Device | Board recorded | Control shown | Card says |
| --- | --- | --- | --- |
| `debra-3c6b3f` | v2, overlay in the file, card listed | **Remove driver** only | "…names respeaker-2mic-v2_0, and this device lists the sound card it creates (seeed2micvoicec). Whether the microphone and speaker work is what the audio checks show." |
| `debra-8518d6`, before enrolment, no choice | none | none | "Choose a board above to see what installing it would do." |
| `debra-8518d6`, before enrolment, after recording v1 | v1 | **none at all** | "This device does not have the install helper yet, so nothing here can change the boot configuration." |
| `debra-8518d6`, after enrolment | v1, overlay in the file, card listed | **Remove driver** only | "…names wm8960-soundcard, and this device lists the sound card it creates (wm8960soundcard). …" |

The third row is the point of the card's rule: a device that cannot install
shows the enrolment command and **no control**, not a disabled one. The fourth
row is the same board after enrolment, with the real control in its place. No
JavaScript error was logged on any page (`window.onerror` and
`unhandledrejection` were captured from the first byte of each load).

Three wording faults were found this way and fixed, all of them sentences that
had been true before the feature existed:

- the opening paragraph still said the only thing the page keeps is the board
  choice;
- the status line had grown into a near-copy of that paragraph;
- and after the restart, the install state still said *"a restart applies it"* —
  to a device that had just restarted, with the card listed directly above it.

The paragraph now names the three things the page can change, the status line
says what none of them proves, and the install state separates three facts: the
line is in the file, a sound card with the driver's name is (or is not) listed
now, and neither is a test of the microphone or speaker. A configured line with
no card listed says the board is not the one the overlay describes, which is the
failure a person actually needs to act on.

## What this does and does not prove

- **Proven:** the HTTP endpoint reaches a root process with no password; the
  helper validates the recorded board and writes exactly one overlay line; every
  change has its own backup; a refused overlay or module writes nothing; no
  install reboots; the socket is group-accessible to `debra` only.
- **Proven, also:** a changed line survives the next boot on the Pi 5, and the
  driver it names binds after that boot; the Restart button restarts the device
  and the page returns on its own; on the Zero 2 W an overlay the image lacks is
  refused before the write and the file is untouched; and a remove-then-install
  cycle restores each Zero's file byte for byte.
- **Not proven:** that a *different* board than the one already on a device will
  bind there — in particular the WM8960 overlay on the Pi 5, whose measured
  WM8960 result is on the Zero 2 W — or that any board the repository has never
  held in hand works. The Pi 5 restart tested the v2 board it already had, not a
  switch.
- **Not proven, and known open:** the ReSpeaker v2 path uses the kernel's
  `respeaker-2mic-v2_0` overlay, which names `tlv320aic3x` while the board
  carries a TLV320AIC3104. The card binds here and binds again after a restart;
  the family mismatch is still not explained. A card binding is not a working
  microphone, and no capture or playback was measured in this test.

## Files

- `control/setup/hat_install.py` — the helper and `--enroll`
- `control/setup/debra-hat.socket`, `control/setup/debra-hat@.service`
- `control/web/hats.py` — the one board table both programs read
- `control/web/server.py` — `/api/setup/hat/install|remove|restart`, socket client
- [design note](../../design/hat-driver-install.md) — why a socket, not `sudo`
