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

## Two boards read, not written

| Board | Helper socket | `respeaker-2mic-v2_0` on image | v2 row reports |
| --- | --- | --- | --- |
| `debra-3c6b3f` (Pi 5) | present | yes | installable |
| `debra-8518d6` (Zero 2 W) | absent (needs a password to enrol) | **no** | *"This image does not carry the respeaker-2mic-v2_0 overlay."* |
| `debra-f943dc` (Zero W) | absent (needs a password to enrol) | yes | installable |

The preflight refusal is real, not theoretical: the Zero 2 W's 64-bit image has
`wm8960-soundcard.dtbo` but no `respeaker-2mic-v2_0.dtbo`, so that row is
reported un-installable per board rather than failing after the write. The helper
checks the same two facts again before it writes.

## What this does and does not prove

- **Proven:** the HTTP endpoint reaches a root process with no password; the
  helper validates the recorded board and writes exactly one overlay line; every
  change has its own backup; a refused overlay or module writes nothing; no
  install reboots; the socket is group-accessible to `debra` only.
- **Not proven:** that the WM8960 overlay binds a ReSpeaker v1 board on *this*
  Pi 5 (the measured WM8960 result is on the Zero 2 W), that a changed line
  survives the next boot on this device, or that any board the repository has
  never held in hand works. The **Restart device** button has never been pressed:
  it would interrupt the lab voice satellite for about a minute.
- **Not proven, and known open:** the ReSpeaker v2 path uses the kernel's
  `respeaker-2mic-v2_0` overlay, which names `tlv320aic3x` while the board
  carries a TLV320AIC3104. The card binds here; the family mismatch is not
  explained by this test.

## Files

- `control/setup/hat_install.py` — the helper and `--enroll`
- `control/setup/debra-hat.socket`, `control/setup/debra-hat@.service`
- `control/web/hats.py` — the one board table both programs read
- `control/web/server.py` — `/api/setup/hat/install|remove|restart`, socket client
- [design note](../../design/hat-driver-install.md) — why a socket, not `sudo`
