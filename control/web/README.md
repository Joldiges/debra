# Local browser controls — prototype

Reusable Python-standard-library service and local HTML/CSS/JavaScript, not a
complete appliance or an internet-facing administration server. Current scope:
native **selected-sink volume and mute**, plus read-only hardware/resources and
service probes. See the [web requirements](../../docs/design/web-control.md)
and [roadmap](../../docs/roadmap.md#browser-first-device-control).

## What it changes

- Moving the slider only previews. **Apply volume** writes the explicit native
  PulseAudio/PipeWire sink, linking its channels. Mute is a separate write.
- Starting, installing, polling, reconnecting and stopping never restore or set
  volume. No sound, microphone recording or test tone is generated.
- No fallback sink, package installation, sudo, component restart, Wi-Fi change,
  LED write, update or firmware operation is exposed.
- The selected sink must be the output used by speech/music; this does not
  reroute existing streams. Percent is not perceived loudness or a safety limit.
- CPU counters need two samples. Missing readings say unavailable. PMIC 5 V is
  distinct from CPU voltage; not every board supports it.
- Service found/active/enabled does **not** prove installation, configuration,
  pairing or successful end-to-end operation. Bluetooth proxy and Music
  Assistant server detection are not implemented.

## Security boundary

Use only on a **trusted local network**. HTTP does not encrypt the key or protect
against a hostile network peer altering the page. Do not port-forward it,
publish it through a tunnel, or reuse another service's password.

In the default `--auth key` mode, one device bearer key protects status reads and
volume/mute writes, but **not** `GET /api/devices`: this public pre-pairing
inventory discloses the configured device names, addresses and labels to any
reachable client that passes the Host and cross-site checks. Do not put secrets
in the list. The installer and server also accept `--auth none`, a development
bypass: any reachable client can read full status and use the audio controls
without a key. Use it only if that exposure is acceptable.

The key is kept in
an owner-only file on the device and browser `sessionStorage` for the tab;
Disconnect clears that tab, not other tabs or already submitted operations.
The service validates explicit Host authorities and same-origin requests, uses
only local assets, refuses embedding, and bounds workers, bodies and command
timeouts. These are useful safeguards, **not a hostile-LAN/DoS guarantee**.
Production enrollment, TLS, key rotation and multi-user access remain backlog.
An overall 15-second deadline closes slow-drip requests, bounds backend waiting
and command timeouts, and prevents expired queued writes from starting. An
already-started native command may have applied even if its response is lost;
read the current state before retrying. A disconnected tab cannot cancel it.

## Prepare on a named, authorized device

Do not run the installer on the development computer by mistake. Use the ordinary
user that owns the device's PipeWire/PulseAudio session. Prerequisites: Linux,
Python 3.10+, `pactl` with JSON support, systemd user services, and an already
working audio session. No dependency manager is needed for this stdlib slice.

1. Copy the reviewed `control/web/` directory to a private staging directory on
   the device, or use a reviewed checkout. The installer copies only four fixed
   runtime files, never a repository or `.local/`.
   The commands below assume the checkout root is the working directory, so
   `control/web/install.py` resolves. If you staged the folder somewhere else,
   run the installer by its staged path from the directory that *contains*
   `control/`, or use an absolute path; nothing else depends on the layout.
2. Record existing native sink volume/mute without changing them:

   ```sh
   pactl --format=json list sinks
   ```

   Select the exact `name`, not `@DEFAULT_SINK@` or a friendly description.
   Record existing `debra-web.service` state if upgrading.
3. On the device, replace the example sink/hostname with verified values:

   ```sh
   python3 -B control/web/install.py \
     --sink 'alsa_output.REPLACE_WITH_REAL_SINK' \
     --bind 0.0.0.0 --port 8787 \
     --host debra-example.local:8787
   ```

   Repeat `--host` for an authorized IP authority if mDNS is unreliable. This
   does not rename the device or configure DNS, mDNS or the firewall.
   Loopback-only installation uses `--bind 127.0.0.1` and
   `--host 127.0.0.1:8787`. Never broaden firewall/network access to work around
   failure without separate agreement.
4. The installer prepares files only. It reports release ID, service path,
   `changed`, and the previous-unit path when upgrading. It does **not** print
    the key. Review the generated unit before explicitly starting a fresh install:

   ```sh
   systemctl --user daemon-reload
   systemctl --user enable --now debra-web.service
    systemctl --user is-active debra-web.service
    ```

    **For an upgrade**, `enable --now` does not restart an already-running old
    release. After reviewing the replacement unit, explicitly activate it:

    ```sh
    systemctl --user daemon-reload
    systemctl --user restart debra-web.service
    systemctl --user is-active debra-web.service
    systemctl --user show debra-web.service -p ExecStart -p MainPID
    ps -p "$(systemctl --user show debra-web.service -p MainPID --value)" -o args=
    ```

    Confirm that `ExecStart` names the installer's reported
    `releases/<release>/server.py`, and that the running PID's arguments name
    that same path. The prototype has no status release-ID field; the unit alone
    does not prove which process is running. Restart only `debra-web.service`, never the audio,
    speech or music services as part of a web upgrade.

   No root or new lingering setting is requested. If the user manager does not
   survive logout, diagnose that separately; don't silently change system policy.
5. Open the address you passed to `--host` — the example above uses
   `debra-example.local:8787`, which is a placeholder, not a real hostname. Use
   the device's verified address and port. Read
   `~/.config/debra/web/access.key` in a private terminal on the device and enter
   it in the page. Never paste it into chat, Git, logs or a query string. Optional
   `/#key=<device-key>` enrollment uses a fragment and removes it from the current
   URL, but copying links exposes the key and is not the preferred shared guide.
6. First verify read-only status and unchanged native volume/mute. Do not click
   Apply/mute or play a sound as a deployment test. Audio changes require the
   user's deliberate interaction or separately authorized testing.

## Files and repeatability

| Path on device | Purpose |
| --- | --- |
| `~/.local/share/debra/web/releases/<sha256>/` | Fixed runtime payload, content-addressed; old releases retained |
| `~/.config/debra/web/access.key` | Persistent device key, owner-only regular file |
| `~/.config/debra/web/.access-key.staged-*` | Private key-publication artifacts; retained, not alternative active keys |
| `~/.config/debra/web/hardware.json` | Optional retained `hat`/`speaker` string labels; not hardware verification |
| `~/.config/debra/web/devices-<sha256>.json` | Private, content-addressed device list referenced by its unit; previous lists retained |
| `~/.config/systemd/user/debra-web.service` | Generated user service; no key in arguments |
| `~/.local/share/debra/web/previous-units/` | Previous generated service files, retained for rollback |

State/application directories are owner-only. An identical installation preserves
the key and service byte-for-byte. Unmanaged services and modified releases are
refused, not overwritten. Interrupted copying retains private staging files;
retry publishes a complete release. Interrupted unit replacement retains the old
unit and its backup; retry uses a fresh pending file. No automatic cleanup.
The key is fully written to a private staging file before atomic no-replacement
publication; interrupted staging cannot poison the active key. Completed staging
artifacts are also retained privately. Invalid pre-existing active keys are
refused, never silently replaced.
These checks protect ordinary failure paths, not against a malicious same-user
process modifying files concurrently. Back up this state privately before
replacing a device; do not distribute it with an image.
Injected write/publication failure recovery is tested, **not abrupt power-loss
durability**: release/unit publication has no complete filesystem flush protocol,
and neither filesystem integrity nor sudden-power-loss restoration is proven.

An optional `--devices <path>` JSON array supplies the public inventory. Each
entry has a `name`, `url` and optional `label`. URLs must use HTTP, an explicit
port from 1 to 65535, and a DNS-style ASCII hostname or canonical IPv4 address;
paths other than `/`, whitespace, control characters, credentials, `?` and `#`
are refused. The server returns lowercase hostnames and scheme, a decimal port
and a trailing slash. Both server and browser apply this same restricted form.

## Stop and roll back without touching audio

Fresh install rollback:

```sh
systemctl --user disable --now debra-web.service
```

Leave the files/key in place for inspection or a later reinstall. No deletion
is necessary; speech/music services and their settings are independent.

Upgrade rollback: use the **exact `previous_unit` path returned by that upgrade**,
not an arbitrary newest file. Preserve the current unit privately first. Then:

```sh
systemctl --user stop debra-web.service
cp -- '<previous_unit>' ~/.config/systemd/user/debra-web.service
systemctl --user daemon-reload
systemctl --user start debra-web.service
```

The old unit references the retained old release and its own device list, if any.
Units created by older installers may instead reference a shared `devices.json`;
those older lists cannot be recovered from the unit alone if overwritten. Restore
the prior enabled/disabled state too. Confirm status access and unchanged native
volume/mute.
Fixture restoration is tested; device restoration must be recorded separately.
This is **web-component rollback**, not whole-device recovery.

## Development checks

From repository root:

```sh
python -B -m unittest discover -s tests -p test_web.py -v
DEBRA_BROWSER_TEST=1 python -B -m unittest discover -s tests -p test_web_browser.py -v
```

The second check uses an already-installed Chromium with its sandbox enabled
and synthetic responses, never host/device audio. Ordinary full-suite runs skip
that opt-in check. Tests do not establish ARMv6 runtime support, physical audio
quality, browser coverage outside Chromium or hostile-network security.
