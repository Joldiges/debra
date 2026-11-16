# The web portal on the Zero 2 W, and the v1 HAT bound by the in-tree overlay

**2026-11-16 — `control/web/` served from the first test board, and the ReSpeaker
2-Mics v1 HAT came up on 64-bit Raspberry Pi OS using the kernel's own WM8960
overlay.** Two things that had not been on hardware: the browser slice on this
board, and the in-tree audio path on this HAT.

Author: OpenCode session, `openrouter/deepseek/deepseek-v4.1-flash-1017`, variant
not exposed by the host. Board: Pi Zero 2 W, `debra-8518d6`, `192.168.0.99`,
Debian 13 (trixie) aarch64, kernel `6.18.50+rpt-rpi-v8`, serial
`00000000468518d6`, ReSpeaker 2-Mics Pi HAT v1 (WM8960).

## Why it was missing

The setup service in `control/setup/` and the browser slice in `control/web/` are
separate installs. The first was installed and tested; the second had never been
installed on this board, so nothing was listening on 8787.

It could not simply be installed: `install.py` requires `--sink` unless
`--restore` is given, and the board had no sound server at all — no `pactl`, no
PipeWire, only the `vc4hdmi` ALSA card. The web slice needs a real sink to name.

## Audio: the in-tree WM8960 path, on 64-bit

`docs/notes/2026-11-15-pi-zero-microphone-paths.md` analysed the **32-bit** image
and left "whether this overlay suits a Seeed v1 board specifically" open. On the
64-bit image the same pieces are present:

```
$ ls /lib/modules/$(uname -r)/kernel/sound/soc/codecs/ | grep wm8960
snd-soc-wm8960.ko.xz
$ ls /boot/firmware/overlays/ | grep wm8960
wm8960-soundcard.dtbo
```

Two lines in `/boot/firmware/config.txt` (backup kept at
`config.txt.bak-20261116`):

```
dtparam=i2c_arm=on
dtoverlay=wm8960-soundcard
```

After a reboot the card bound on the first attempt:

```
$ cat /proc/asound/cards
 0 [wm8960soundcard]: simple-card - wm8960-soundcard
 1 [vc4hdmi        ]: vc4-hdmi - vc4-hdmi
$ ls /sys/bus/i2c/devices/ | grep 1-001a
1-001a
$ dmesg | grep wm8960
wm8960 1-001a: supply DCVDD not found, using dummy regulator
wm8960 1-001a: supply DBVDD not found, using dummy regulator
wm8960 1-001a: supply SPKVDD1 not found, using dummy regulator
wm8960 1-001a: supply SPKVDD2 not found, using dummy regulator
```

So the Waveshare overlay's pin/I²C description suits this Seeed v1 board. The
codec driver is the maintained in-tree one, not the `seeed-voicecard` DKMS
package, so no vendor build is needed on this image.

**The `dummy regulator` lines are real and unresolved.** The overlay describes no
supplies, so the codec binds without regulator control. The card exists and
PipeWire reads it; whether the codec is actually powered correctly for playback
and capture was not measured. This is the next audio question, not a solved one.

## PipeWire and the portal

Packages: `pipewire`, `wireplumber`, `pipewire-pulse`, `pipewire-alsa`,
`pulseaudio-utils` (for `pactl`), `alsa-utils`, `i2c-tools`. The `libspa-0.2-alsa`
name does not exist on trixie; `pipewire-alsa` is the package that is there.

The portal needs the user manager to outlive the SSH session, so
`loginctl enable-linger debra` was set. That is a deliberate system-policy change
and is why the service is still up when nobody is logged in; the web README says
not to change it silently, and this record is the statement.

Installed from the **committed** tree (`git archive HEAD control/web`), not the
working tree, which holds another worker's uncommitted edits:

```
$ python3 -B control/web/install.py \
    --sink 'alsa_output.platform-soc_sound.stereo-fallback' \
    --bind 0.0.0.0 --port 8787 \
    --host debra-8518d6.local:8787 --host 192.168.0.99:8787
release: 9f532517e4fecc798fd42c6de30b2d3bf5c1046215082cb9bef19a84865aceca
```

## Evidence

| Check | Result |
| --- | --- |
| `http://debra-8518d6.local:8787/` from the Fedora host | `200`, `text/html` |
| `http://192.168.0.99:8787/` | `200` |
| Listening | `0.0.0.0:8787` |
| `/api/status` without a key | `403` |
| `/api/status` with `Host: 127.0.0.1:8787` | `{"error": "Unrecognized host"}` — the allowlist working |
| `/api/status` with an allowed host and the key | `auth: key`, `audio.available: true`, sink `alsa_output.platform-soc_sound.stereo-fallback`, `percent: 40`, `muted: false` |
| Power | `throttle_flags: 0x0`, no undervoltage now or since boot |
| After a reboot | all four user services active, `debra-web.service` `Result=success`, `NRestarts=0`, portal `200` on both addresses |
| `debra-setup.service` | untouched: enabled, `Result=success`, `NRestarts=0` |

The access key is `~/.config/debra/web/access.key`, mode `0600`, read on the
device only. It is not in this note, the repository or the logs.

## Not done

- **No sound was played and no audio was written.** The sink exists and reads
  40%; that is not proof the codec amplifies. The web README says not to click
  Apply or play a tone as a deployment test, and that stands.
- **No capture test.** The microphones, the `dummy regulator` supplies and the
  WM8960's actual power rails are unmeasured.
- No browser-driven check of this deployment (the page was fetched with `curl`),
  no access-key rotation, no firewall rule, and no captive portal.
- The sink appears as `Built-in Audio Stereo` through WirePlumber's ACP
  fallback: there is no UCM profile for this card, which is the profile question
  the earlier note predicted, not a fault.

## Addendum: the key failed with `{"error": "Not found"}`, and the board now runs the bypass

Added the same day, after James tried the page and reported that the key would
not connect.

**The key itself works.** From the device, `GET /api/status` answers `401
{"error": "Access key required"}` without it and `200` with it. What James saw
was a different failure:

```
$ curl -s -o /dev/null -w '%{http_code}\n' 'http://…:8787/?key=abc'
404        {"error": "Not found"}
$ curl -s -o /dev/null -w '%{http_code}\n' 'http://…:8787/index.html'
404        {"error": "Not found"}
```

The key form is JavaScript-only: `app.js` attaches the submit handler and calls
`/api/status` with `Authorization: Bearer …`. If the form is submitted natively —
Enter pressed before `app.js` has run, or scripting blocked — the browser does a
plain `GET /?key=…`, and the server serves the page only at an exact `/`, so the
person gets raw JSON. `/index.html` fails the same way. **This is a real defect
in the page/server pair and is not fixed here**: `control/web/` belongs to
another worker's packet, and a change there needs its own review. The fix is
either a form that cannot submit without JavaScript or a server that answers
`/?…` with the page and a clear message.

**James's judgement on the key is the product judgement already recorded.**
[Browser enrollment](../../design/browser-enrollment.md) is the decided path: the
password is chosen during setup behind the card's setup-network password, so
nobody types a 43-character key. That implementation is not written. The same
decision sanctions a development bypass, so this board was switched to it:

```
$ python3 -B control/web/install.py --sink 'alsa_output.platform-soc_sound.stereo-fallback' \
    --bind 0.0.0.0 --port 8787 --host debra-8518d6.local:8787 --host 192.168.0.99:8787 \
    --auth none
previous_unit: …/previous-units/20261116T052853951893Z.service
```

The running unit names `--auth none`, `/api/status` reports `"auth": "none"`, and
the page offers **Continue without a key (development)** with its warning banner.
That is a real security tradeoff, stated plainly: anyone who can reach port 8787
on the household LAN can read this device's status and change its volume and
mute, with no credential. It is a development mode, not the product. Reverting is
the same install without `--auth none`, then `systemctl --user daemon-reload &&
systemctl --user restart debra-web.service`; the previous unit is retained.
