# Local browser controls — prototype

Reusable Python-standard-library service and local HTML/CSS/JavaScript, not a
complete appliance or an internet-facing administration server. Current scope:
native **selected-sink volume and mute**, plus read-only hardware/resources,
service probes and a **read-only Setup card** (HAT, tools and settings, updates)
where every choice is disabled with its reason. See the
[web requirements](../../docs/design/web-control.md)
and [roadmap](../../docs/roadmap.md#browser-first-device-control).

## What it changes

- Moving the slider only previews. **Apply volume** writes the explicit native
  PulseAudio/PipeWire sink, linking its channels. Mute is a separate write.
- Starting, installing, polling, reconnecting and stopping never restore or set
  volume. No sound, microphone recording or test tone is generated.
- Most status is cached for two seconds; the selected sink's audio state is
  re-read on every status request, including cache hits.
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
inventory discloses configured and discovered device names, addresses and labels to any
reachable client that passes the Host and cross-site checks. Do not put secrets
in the list. The installer and server also accept `--auth none`, a development
bypass: any reachable client can read full status and use the audio controls
without a key. Use it only if that exposure is acceptable.
`/api/status` reports the active mode in its `auth` field (`key` or `none`);
this is not a browser enrollment or revocation status.

The key is kept in
an owner-only file on the device and browser `sessionStorage` for the tab;
Disconnect clears that tab, not other tabs or already submitted operations.
The service validates explicit Host authorities and same-origin requests, uses
only local assets, refuses embedding, and bounds workers, bodies and command
timeouts. These are useful safeguards, **not a hostile-LAN/DoS guarantee**.

Requests a browser marks `Sec-Fetch-Site: cross-site` are refused, with one
deliberate exception: a top-level navigation (`Sec-Fetch-Mode: navigate`,
`Sec-Fetch-Dest: document`) for the page's own static files. That is what a
Switch link from another Debra looks like, and refusing it showed the person a
JSON error instead of the device. The exception covers no API path and no write,
and the page it serves is the same one anyone reaches by typing the address.
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
   the device, or use a reviewed checkout. The installer copies only five fixed
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
   The installer requires a listening port from 1024 to 65535, and every
   explicit `--host` authority must use that same port.
   Loopback-only installation uses `--bind 127.0.0.1` and
   `--host 127.0.0.1:8787`. Never broaden firewall/network access to work around
   failure without separate agreement. The installer requires `--host` even for
   loopback; the server run directly with that bind and no `--host` defaults to
   `127.0.0.1:<port>`.
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
    `releases/<release>/server.py`, with `discovery.py` beside it, and that the
    running PID's arguments name that same path. The prototype has no status
    release-ID field; the unit alone does not prove which process is running. Restart only `debra-web.service`, never the audio,
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

An unreadable, malformed or invalid `hardware.json` refuses server startup with
an error message; correct it or preserve it elsewhere before starting again.
The generated unit is configured to retry on failure.

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

An optional `--devices <path>` JSON array supplies configured entries for the
public inventory. It allows at most 50 entries; each has a `name` of 1–64
letters, digits, dots, dashes or underscores, a `url` of at most 200 characters,
and an optional `label` of at most 80 characters. URLs must use HTTP, an explicit
port from 1 to 65535 **except 80**, and a DNS-style ASCII hostname or canonical
IPv4 address; paths other than `/`, whitespace, control characters, credentials,
`?` and `#` are refused. The server returns lowercase hostnames and scheme, a
decimal port and a trailing slash. Both server and browser apply this same
restricted URL form.
The installer listening-port rule above is separate from the device-link rule.
Port 80 is refused on purpose: a browser drops a default port, so
`http://device.local:80/` becomes `http://device.local/`, and the Host check this
service applies would then reject the page it had just linked to. An entry that
cannot round-trip is worse than one that never appears.

Local `_debra._tcp` mDNS discovery is attempted when the web service runs; it needs
`avahi-browse` and a working Avahi daemon, but no Python packages. The first
scan starts in a background thread at startup and is bounded by an 8-second
command timeout. Announcements must have a `.local` host and a port from 1 to
65535; the hub then applies the device-link rule above, so port 80 is not listed.
Until the scan finishes, only configured entries are shown. After
each scan the thread waits 30 seconds before starting the next; during a scan
the previous result remains cached. A failed, timed-out or empty scan clears
discovered entries, leaving the configured list. The page refreshes the list
every 5 seconds, including before pairing. Configured entries come first and
win when URLs match; each URL appears once. Discovered records use the same
name, label and URL checks as configured records.
The server also browses its own advertisement if Avahi returns it; repeated
announcements with the same instance and port coalesce across interfaces, and
matching canonical URLs merge. Different names/ports or URL aliases for the same
physical device are not generally recognized as one identity.

`/api/devices` reports each entry's `source` as `configured`, `discovered` or
`configured+discovered`. Its `discovery` block reports `enabled`, `found`,
`seconds_since_scan` and `error`. The configured list remains available without
Avahi, even when discovery fails or cannot start.

Discovery is a convenience, **never authentication or proof of reachability**:
any local peer can make an announcement, and plain HTTP cannot authenticate the
destination. Verify the destination before entering a key. Discovery can also
be unavailable or blocked by the network; keep the configured list as a
fallback. The installed server and `tools/discover.py` use the same browse and
parsing implementation in `control/web/discovery.py`.

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
python3 control/web/install.py --restore '<previous_unit>'
systemctl --user daemon-reload
systemctl --user start debra-web.service
```

`--restore` writes a complete file and renames it over the unit, so an
interruption leaves either the old unit or the new one and never a truncated
file that cannot start. It refuses a file with no `ExecStart` line and starts
nothing itself. A `cp` would truncate the destination before writing, which is
why it is not used here.

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
