# Local browser controls — prototype

Reusable Python-standard-library service and local HTML/CSS/JavaScript, not a
complete appliance or an internet-facing administration server. Current scope:
native **selected-sink volume and mute**, plus read-only hardware/resources,
service probes, a **Setup card** (HAT, tools and settings, updates) that is
read-only apart from recording which audio board is fitted, and a **Planned task
list** of the jobs the appliance will do later. See the
[web requirements](../../docs/design/web-control.md), the
[page design study](../../docs/design/device-page-ux-2026-11-16.md)
and [roadmap](../../docs/roadmap.md#browser-first-device-control).

## The page

One document, phone-first, no framework, no build step, no external asset. In
order down the page: the device's name and board, a sticky section bar (Audio,
Health, Device, Components, Setup, Tasks), then **speaker volume** — the only
write — followed by read-only health, hardware, service detection, the planned
setup choices, the planned tasks, and finally the list of other Debras on the
network. Everything read once rather than operated is a native `<details>`;
section headings and every warning stay outside them.

This order is deliberate and measured, not stylistic. Before it, the page
opened on "switch to another Debra" and the volume slider was 1262 px down a
6733 px document on a 390 px phone; it is now on the first screen of a 3184 px
one. The section bar was 16-19 px tall, in an order that disagreed with the
document, with no indication of where you were; every entry is now a 44 px row
that follows both taps and scrolling. Anyone changing this order should re-run
the check named in [Development checks](#development-checks), which fails if the
first screen loses the volume control.

**Planned means text.** A capability that does not exist is a title, a `Planned`
badge and one sentence saying what it will do and why it cannot yet. It is never
a disabled button or a greyed field: a disabled control still shows a shape that
cannot be honoured, still has to explain itself, and runs any handler attached
to it the moment anything enables it. The Setup card used to build two radios,
three selects and three buttons this way; it now builds none, and an offline
check fails if a control builder returns.

**Missing is named.** A reading the device does not have is shown as
`Unavailable` inside the list, and a reading nothing collects — CPU-core voltage,
which no collector reads — has its own row saying so and marked Planned. The one
voltage a Pi 5 does report is the 5 V supply and is never presented as CPU-core
voltage. Reading *age* is unknown: the device says when it sent a reading, not
when it measured it, and the page says so rather than labelling its own clock as
an observation time.

## What it changes

- Moving the slider writes the explicit native PulseAudio/PipeWire sink a
  moment after it stops moving, linking its channels. There is no Apply button:
  a person who moves a slider expects the device to follow, and the extra press
  is the one they forget. A drag is coalesced into one write with the newest
  value winning, and a write already in flight defers rather than queueing
  behind itself, so the last value is always the one the device ends up with.
  Mute is a separate write.
- **A write is never repeated by the page itself.** When a write's outcome is
  unknown or was refused, **Send that level again** appears beside the control,
  and only while there is something to retry. A level that could not be sent (no
  usable output, a device that is not answering, a disconnected tab) is labelled
  as not applied rather than left looking as if it were sent.
- **Two deliberate checks, and no reading can replace them.** *Test speaker*
  plays half a second of 440 Hz tone at about −18 dBFS through the selected
  sink, built in memory as a WAV, written to a private temporary file for the
  length of the command and removed with it. It never changes volume, mute or
  device, never falls back, and is refused with a reason when the output is
  muted rather than played into silence. *Test microphone* records about a
  second from the device's own default input with `parec`, reduces it to one
  peak figure and drops the samples: nothing is written to the state directory,
  logged or sent anywhere but back to the browser that asked. The recording is
  a number of samples rather than a wall-clock budget, so a slow `parec` start
  on a Zero cannot shorten it to a fraction of a second, and a muted input is
  refused with its reason instead of being reported as silence. Silence is
  reported as silence; the page never turns a level into "the microphone
  works". One of each runs at a time. `POST /api/audio/test-output` and
  `POST /api/audio/test-input` take an empty JSON object (`{}`).
- The outcome of a write is reported beside the control that caused it, under
  the slider and mute: a rejection or an unanswered change explains itself
  where the person is looking. The page-level error region carries read
  failures; a refused key is named on the welcome card instead.
- **A refused key is forgotten and named.** A key the device rejects (`401`) is
  removed from the tab, the welcome card says so, and the page still checks
  whether the device runs without a key — a dead credential must not hide the
  one way in. A key is written to the tab only after a status read has accepted
  it; one that has not been accepted yet stays in memory and is retried by the
  poll, never replayed from storage on the next reload.
- **A key in the address is named, not replayed.** The form posts, so a submit
  without JavaScript does not put the key in the URL; an older `/?key=...`
  address is served the page, which says it will not accept a key there.
- A page that cannot check for keyless access says why on the welcome card,
  including when the device does not answer or answers with an error. Older
  browsers without `AbortSignal.timeout` use a fallback.
- Starting, installing, polling, reconnecting and stopping never restore or set
  volume, and generate no sound. The only sound and the only microphone capture
  in this code happen when a person presses **Test speaker** or **Test
  microphone**, one press at a time, and neither outlives the press.
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
- A read failure is named at the top of the page, with **Try reading again**:
  that control reads and only reads, so it can never become a replay of a write
  whose outcome was uncertain. A failed poll labels the readings below it as the
  last ones the device sent, with the time this page received them.
- An output the device names but cannot use disables every control on the card,
  and the card says why, in the device's own words. With nothing to read, the
  level says **No level** rather than showing the slider's default position as
  though it were a measurement.
- The Setup card offers a list of the boards a person might have fitted
  (ReSpeaker 2-Mics v2, ReSpeaker 2-Mics v1, Waveshare WM8960, or no HAT), which
  records the choice in `hardware.json` in the private state directory. That
  record is what the person asked for: it is not a detection and it changes
  nothing. A device with no state directory to keep the choice in shows no
  control at all rather than a dropdown that forgets. Next to the list the card
  states three separate facts, because a silent speaker otherwise has no
  traceable cause: what the EEPROM named, what was recorded, and whether an
  ALSA card with the driver's name is present.
- **Install driver** acts on the recorded choice, not on a request body: the
  server sends `{"verb": "install", "board": "<recorded id>"}` to a small root
  helper ([`control/setup/hat_install.py`](../setup/hat_install.py)) and never
  writes the boot configuration itself. The helper validates the id against the
  same table the page reads ([`hats.py`](hats.py)), refuses a board whose overlay
  or kernel module this image does not carry, copies `config.txt` beside itself
  first, writes atomically, reads the file back, and restores the copy if what
  came out is not what was asked for. **Remove driver** takes the managed overlay
  out again; choosing "No HAT" does the same thing. A **Restart device** button
  appears only after this tab has changed the file, and asks for confirmation
  before sending `{"confirm": "restart"}`. The helper never restarts as a side
  effect, and no restart happens without that button.
- The helper must be **enrolled once**, by the device's owner, with a password:
  `sudo python3 -B control/setup/hat_install.py --enroll`, which the installer
  prints. It installs the helper to `/usr/local/sbin/debra-hat-install`, its
  table to `/usr/local/lib/debra/hats.py`, and a **socket-activated unit** that
  runs it as root for one request. The request arrives as JSON on the socket
  connection, which only the page's own account group can open. Until then the
  card shows that one command and no control at all.
- The transport is a socket rather than `sudo` because this service runs with
  `NoNewPrivileges=yes`: a setuid `sudo` could not escalate from it at all, and
  removing that line to allow one would trade real hardening for convenience.
  There is no passwordless `sudo` rule on the device. The card only knows
  whether the socket exists; whether it will answer is what pressing the button
  finds out, in one round trip.
- Installing proves the **file** changed, not that the driver works. The card
  says so: the boot line is one fact, the ALSA card is another, and whether the
  codec binds is what the restart and `/proc/asound/cards` show afterwards.
- The Setup card's HAT rows report a **family match**, not an identification: the
  EEPROM product names a ReSpeaker/Seeed two-microphone board, and the exact
  model and revision are not established. The two-microphone match has a number
  boundary, so `12-Mics` in a product string is not read as `2-mic`. The "No HAT:
  3.5 mm jack or USB audio" row is an alternative rather than a board, so it is
  not asked of the EEPROM at all and does not claim the EEPROM fails to name a
  ReSpeaker. A WM8960 codec does not name its vendor, so the Seeed v1 and the
  Waveshare boards are listed apart and both report the same card: the person
  knows which board they bought even when the driver cannot say.
- A **Device tasks** card lists the jobs a person will come to the page for —
  changing Wi-Fi, restarting speech or music, keeping a known-good copy,
  maintenance over SSH, speaking through the device — and marks every one
  **Planned** with the roadmap id it waits on. The rows are static markup with
  no control of any kind, because there is no device state to report about work
  that has not been built. They are there so the intended shape is visible and
  testable, not to suggest the tasks are close.

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
an owner-only file on the device and browser `sessionStorage` for the tab, and
only after the device has accepted it; until then it stays in memory and the
poll may retry it, but a reload cannot replay it from storage. Disconnect clears
that tab, not other tabs or already submitted operations.
Protected status and Setup reads are bound to the session they started in, so a
response that was still in flight when the tab disconnected is discarded instead
of repainting the previous device's readings or build choices. The public
pre-pairing device inventory is deliberately not session-bound: it carries no
device state and is fetched before a session exists.
The service validates explicit Host authorities and same-origin requests, uses
only local assets, refuses embedding, and bounds workers, bodies and command
timeouts. These are useful safeguards, **not a hostile-LAN/DoS guarantee**.

Requests a browser marks `Sec-Fetch-Site: cross-site` are refused, with one
deliberate exception: a top-level navigation (`Sec-Fetch-Mode: navigate`,
`Sec-Fetch-Dest: document`) for a page route. That is what a
Switch link from another Debra looks like, and refusing it showed the person a
JSON error instead of the device. The exception covers no API path and no write,
the query is ignored and never reflected, and the page it serves is the same one
anyone reaches by typing the address.
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
Discovery additionally needs `avahi-browse` from the Debian `avahi-utils`
package on the machine running the server; without it the page reports
"Discovery problem: avahi-browse is not installed" instead of listing devices.
The page itself needs a JavaScript-capable browser: with scripting off it cannot
read status or offer the development bypass, and it says so in a `<noscript>`
line. Neither dependency is installed by this installer.

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
   Add `--label 'Lab Pi 5'` to publish a friendly name that another Debra's
   device list shows; without it the device publishes its hostname alone. The
   label is one printable line of at most 80 characters.
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
| `~/.config/debra/web/hardware.json` | Optional retained `hat`/`speaker` string labels plus the board a person chose (`hat_choice`); not hardware verification and not an installation |
| `/usr/local/sbin/debra-hat-install` | The root helper, installed only by `--enroll`; writes the boot configuration for one board |
| `/usr/local/lib/debra/hats.py` | The board table the helper reads; the same file the page's table comes from |
| `/etc/systemd/system/debra-hat.socket` | The socket the page connects to, `0660`, group = the page's account |
| `/etc/systemd/system/debra-hat@.service` | One helper process per connection, `StandardInput`/`Output=socket` |
| `/boot/firmware/config.txt.debra-<stamp>` | Timestamped copy the helper makes before every change; never overwritten |
| `~/.config/debra/web/devices-<sha256>.json` | Private, content-addressed device list referenced by its unit; previous lists retained |
| `~/.config/systemd/user/debra-web.service` | Generated user service; no key in arguments |
| `~/.local/share/debra/web/previous-units/` | Previous generated service files, retained for rollback |

An unreadable, malformed or invalid `hardware.json` refuses server startup with
an error message; correct it or preserve it elsewhere before starting again. The
allowed keys are the `hat` and `speaker` labels (up to 160 characters) and
`hat_choice`, which must name one of the boards the page offers or be empty; the
file this server writes always passes that check, because a file it writes but
cannot start from is a service that stops coming back. A
choice is written by `POST /api/setup/hat` with `{"choice": "<option id>"}` (or
`""` to clear it), atomically and owner-only, keeping every other retained field;
an unknown id is refused with a `400` and changes nothing. The three boot actions
are separate paths and take no board: `POST /api/setup/hat/install` (`{}`),
`POST /api/setup/hat/remove` (`{}`) and `POST /api/setup/restart`
(`{"confirm": "restart"}`). A helper refusal is a `409` with the helper's own
sentence; a request body that names a board is a `400`.
The generated unit retries on failure, and stops retrying after four attempts in
five minutes (`StartLimitIntervalSec=300`, `StartLimitBurst=4`, in `[Unit]`).
Without that limit a unit that cannot start — a refused `hardware.json`, for
example — restarts every three seconds for ever and leaves only a journal line.

State/application directories are owner-only, and every file this installer
creates is owner-only from the moment it exists rather than after a later
`chmod`. An identical installation preserves the key and service byte-for-byte.
Unmanaged services and modified releases are refused, not overwritten.
Interrupted copying retains private staging files; retry publishes a complete
release. Retained releases are content-addressed, and each install re-checks
them: a retained release whose files no longer match its name is reported as a
warning, and `--restore` refuses a unit that runs one. Otherwise a rollback
would restore a service that cannot start. Interrupted unit replacement retains the old
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

### This device publishes its own announcement

The serving process publishes its own `_debra._tcp` record, so other Debras can
find it. `avahi-publish-service` is an ordinary user program, so this needs no
root and no second unit: it runs as a child of the server and dies with it, and
a stopped server stops being advertised instead of leaving a record pointing at
a port nothing answers. A server bound only to loopback is not advertised,
because no other device could reach it; `--no-announce` switches it off
deliberately. Both cases give a reason rather than leaving the page to guess
from silence.

`/api/devices` therefore also carries an `announcement` block: `enabled`,
`running`, `instance`, `port`, `label`, `spawns`, `seconds_running`, `error`
and `reason`. Failure is reported, never hidden. A missing publisher is not
retried; a publisher that exits is retried every few seconds and its last line
becomes the reported `error`. Before this existed, one device carried a
hand-written `debra-advertise` user unit and every other device truthfully
reported that it could find only that one device.

`refused` is one entry per **refused record the scan returned**, not per distinct
sentence and not a count of physical advertisements. The parser reports only an
instance name and a reason, and two records can share both (port 0 and port 65536
are refused for the same stated reason), so a per-list-entry identity is kept
until the count is made; the hub's own revalidation is keyed by the record it
refused. Two limits follow: avahi reports a resolved record once per interface
and address family, so one refused advertisement seen twice is counted twice;
and two malformed records with the same name and URL merge into one entry. The
page prints that count as refused records rather than as distinct devices.
Naming a refused device twice is better than dropping it.

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
file that cannot start. A `cp` would truncate the destination before writing,
which is why it is not used here.

**`--restore` accepts only the form this installer writes** — the unit must
carry the installer's marker line, and its `ExecStart` must use the installer's
own quoting (every argument double-quoted, with only `\\`, `\"`, `%%` and `$$`
escaped) and the installer's own command shape. A hand-written unit is refused
rather than half-understood: systemd accepts a larger language (`\x20`, single
quotes, `$VAR`), and a decoder that accepts more than it can reproduce has
already validated a different path from the one systemd would start. The marker
is a **format** check, not proof of authorship: anything that reproduces the
marker and the quoting is accepted, so this does not defend against someone who
can already write to the account's files. Within that form it checks:

- an `ExecStart` inside `[Service]` — systemd ignores one in `[Unit]`, and an
  empty `ExecStart=` resets the list, so neither unit has a start command;
- exactly one start command, because `Type=simple` runs one and this installer
  writes one;
- a leading `-` is "ignore failure", not part of the executable path;
- the start command is the shape `install()` writes: an absolute interpreter,
  `-B`, the release's own `server.py`, `serve`, then option/value pairs from the
  installer's own set. A relative script, a command naming no release at all
  (`python3 -B -c 'print(1)'`), or an unknown option is refused instead of being
  checked vacuously — the earlier check skipped every argument that did not
  start with `/`, so those commands passed with nothing examined;
- the options are ones the installed server would accept, because it refuses
  these before it opens a socket: an audio sink is named (it never follows a
  default or a hotplugged device), `--auth` is `key` or `none`, `--port` is an
  unprivileged number, `--state-dir` and `--devices` are absolute, and every
  `--host` is a `hostname:port` the server accepts. A rollback that published a
  command the server rejects reported success for a service that cannot start;
- the entry point is `server.py` at the top of a release under the managed tree,
  and every ancestor of that tree is a real directory. Renaming
  `~/.local/share` and pointing the name at a preserved copy repoints every
  release at once without changing a byte inside one. The entry point must be
  `server.py` itself, not merely one of the five payload files: `discovery.py`
  defines functions and serves nothing;
- every payload file inside that release is a real file, reached through real
  directories without `..` — a link under the release would let the digested
  files be replaced without changing the name the unit is checked against;
- that release is complete (all five fixed payload files) and still matches the
  content address it is named by.

**It restores the file. It does not recover the service.** Nothing is started,
and no check here proves the restored unit starts and stays up — that takes the
`daemon-reload` and `start` steps above and then a check that the service is
active, and a rollback to a release that imports is what the checks are for, not
a substitute for them.
Acceptance by the decoder is not proof of startup either. The installed entry
point is `0600`, and the shape check already refuses a command that runs it
directly; if it were accepted, the kernel would refuse to execute it.

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
python -B -m unittest discover -s tests -p 'test_web*.py' -v
DEBRA_BROWSER_TEST=1 python -B -m unittest discover -s tests -p 'test_web_browser.py' -v
```

The first covers `test_web.py`, `test_web_setup.py` and the installer tests. The
second uses an already-installed Chromium with its sandbox enabled and synthetic
responses, never host/device audio. Ordinary full-suite runs skip that opt-in
check.

The layout checks are geometric, not visual: they open the page in a 390 px
iframe (headless Chromium clamps a window to 500 px) and assert where things
are. These are the ones that fail if the order above is undone:

- `test_the_device_and_its_volume_come_first_on_a_phone` — document order, the
  keyless warning before the controls, volume/Apply/Mute inside the first
  screen, unique ids, every section link resolving.
- `test_the_section_bar_is_tappable_and_knows_where_you_are` — 44 px targets,
  bar order matching document order, exactly one current section after a tap and
  after a scroll.
- `test_setup_card_offers_no_control_at_all` — zero controls, links,
  `tabindex` or interactive roles in the Setup card, and no write when every row
  is clicked, changed or touched.
- `test_a_missing_reading_is_named_and_never_invented` — the supplied voltage
  appears only as the 5 V supply, and the missing-reading row carries no number
  and no state badge.

Tests do not establish ARMv6 runtime support, physical audio quality, browser
coverage outside Chromium, screen-reader behaviour or hostile-network security.
