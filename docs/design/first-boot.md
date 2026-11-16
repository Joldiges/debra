# First boot: from a flashed card to a working device

**Status: partly implemented, 2026-11-16. The online path has run on a device,
but on main's tree, not this branch's; nothing here has raised a radio or served
the page.**

The phase machine, the setup page and the first baseline exist as code under
`control/setup/` and pass offline tests against a recorded fake NetworkManager.
One Zero 2 W has installed the service, been renamed from its serial, captured a
baseline, and run the unit as part of a boot
([result](../testing/results/2026-11-15-zero2w-setup-service-first-run.md)). No
radio has been raised by it, no page has been served, and no join has been
performed by it. Its system unit and installer are tested offline — see
[the setup service](../../control/setup/README.md). Read
[implemented today versus planned](#implemented-today-versus-planned)
before relying on a step.

This page describes the journey James asked for — flash a card, the Pi configures
itself, it raises a hotspot when there is no Wi-Fi, it takes a baseline, then
everything else happens in a browser page — and separates the parts that exist
from the parts that are still a plan. Requirements live in the
[project brief](../project-brief.md); task state lives in the
[roadmap](../roadmap.md), not here.

## The journey as a person experiences it

No Linux vocabulary is needed for these steps, and none is used.

1. Plug the prepared card into the device, connect power, wait.
2. The device has no Wi-Fi of its own yet, so it puts up a small network of its
   own. Its name is `Debra-Setup-` followed by six characters.
3. On a phone, join that network and open the setup page. It is usually served
   at `http://10.42.0.1/`; the card note and the page print whatever address it
   actually bound to.
4. Choose your country if you are asked for one, type the name of your home
   Wi-Fi and its password, and press **Join network**.
5. The page tells you that the setup network is about to disappear. It does, and
   your phone drops off it.
6. If the details were right, the device is now on your home Wi-Fi. Your phone
   rejoins your home network, and you open the device's own page at
   `http://debra-xxxxxx.local:8787/`. That page today has speaker volume, mute
   and read-only status, and nothing else.
7. If the password was wrong, the setup network comes back and the page says
   what happened, so you can try again. Nothing reboots.
8. Choosing the HAT and its drivers, choosing tools and settings, and the update
   and upgrade buttons are **planned**. They do not exist.

Step 8 is the whole second half of the journey the brief describes, and it is the
part the [web configuration scope](web-control.md) covers in detail. This page
stops at "the device is on the network and has a baseline".

## What the device does at each step

Five phases are defined in one closed set
([`state.py`](../../control/setup/state.py)): `unconfigured`, `hotspot`,
`connecting`, `online`, `failed`. One small JSON file is the entire record of
where a device is; it survives a reboot, so a power cut in the middle of setup
does not restart the journey from nothing.

| Phase | Entered when | What is recorded |
| --- | --- | --- |
| `unconfigured` | No state file exists yet, so a blank record is returned and written on first change | `schema: 3`, `phase: unconfigured`, `revision: 0`, an empty hostname, `attempts: 0`, `attempt_claimed: false`, an `updated` timestamp; every other field null |
| `hotspot` | `resume()` finds no routable Wi-Fi uplink, or a fresh start; also what a failed attempt falls back to | `phase`, `hotspot: {ssid, interface}`, `last_error: null`. The setup password is **not** here: it has its own owner-only file beside the state |
| `connecting` | A submission was accepted by the page and the worker entered `join()` | `phase`, `ssid`, `attempts` incremented, `attempt_token`, `attempt_claimed`, `last_error: null` |
| `online` | The adapter returned a Wi-Fi device with a routable IPv4 address | `phase`, `ssid`, `address`, `hotspot: null`, and `baseline` once the capture succeeds; `attempt_token` and `attempt_claimed` are cleared |
| `failed` | The join raised; the setup network could not be raised; or a boot found the device was `online`/`connecting` and is not now | `phase`, a one-line `last_error`, the advanced `revision`, `attempts` and `last_attempt` from the attempt, `attempt_token: null`, `attempt_claimed: false`, `baseline_error` when a baseline attempt failed, and the `hotspot` record when the setup network came back |

Transitions, in full:

| From | To | Trigger |
| --- | --- | --- |
| `unconfigured` | `hotspot` | `resume()` at boot: no uplink, no prior phase |
| `unconfigured` | `failed` | `resume()` tried to raise the setup network and could not (no Wi-Fi interface, or the adapter refused) |
| `hotspot` | `connecting` | `POST /api/join` validated, answered `202`, worker started |
| `hotspot` | `failed` | The join raised; the setup network is raised again with the reason |
| `connecting` | `online` | `connect()` returned an active, routable Wi-Fi uplink |
| `connecting` | `failed` | `connect()` raised; the setup network is raised again with the reason |
| `online` | `failed` | A boot finds no routable uplink; the reason is "The previous network is not reachable" |
| `connecting` | `failed` | A boot finds the last attempt never finished; the reason is "The last attempt did not finish" |
| `failed` | `hotspot` | A boot in `failed` starts a plain setup network again — which clears the reason |
| `failed` | `connecting` | Another submission from the page |

Two things the state file deliberately does not contain. It never holds the
Wi-Fi passphrase: the key belongs to NetworkManager's own keyfile, and a second
copy would be a second place to leak it. And it is not "repaired" when it cannot
be read — an unreadable or unknown state file is an error, because silently
resetting it would hide the fact that a device had already been configured. The
file is written atomically, its directory is `0700` and the file is `0600`.

### The name

The device names itself `debra-` plus the last six characters of the board
serial, lowercased, so the name is stable across re-flashes of the same board and
different between boards. The serial is read from
`/sys/firmware/devicetree/base/serial-number` or `/proc/device-tree/serial-number`,
with a fallback chain if neither can be read. The name is recorded once and not
rewritten. The setup network is named `Debra-Setup-` plus the same six
characters.

The name is the only thing the journey promises. The address on the household
network is not promised, because it is assigned by the household router and does
not exist until after the setup network has already gone — see
[why the page cannot show the address](#what-the-page-cannot-show).

## Implemented today versus planned

"Implemented" below means the decision and the HTTP contract are real and pass
offline tests. It does **not** mean a device has done it. Every row that touches
the operating system is at most `partial`.

| Step | What it is | Status | What is missing |
| --- | --- | --- | --- |
| Repeatable name | Hostname derived from the board serial and recorded once | implemented | Nothing on the decision itself; the derivation is pure code and tested |
| Applying the name | `hostnamectl set-hostname`, an atomic rewrite of the `/etc/hosts` alias, and an unconditional restart of the mDNS responder, so the running system answers to the recorded name | partial | Ran on a Zero 2 W: a live rename kept the connection and the device answered `hostname -f` and `sudo` afterwards, but that was the **earlier draft** — the atomic replace and the unconditional `try-restart` were written after it and are offline-only. Unproven: the shipped mechanism on a board, a rename by a *first* boot, and an image whose cloud-init metadata pins a hostname |
| State across reboots | Versioned JSON schema (`SCHEMA = 3`), atomic owner-only writes, refuses unknown keys and phases; a schema-1 or schema-2 record is migrated on read | implemented | Nothing on the schema. A record from an earlier schema is dropped of retired keys, has the few fields an earlier build could lack filled from a blank record, and is written back; a combination the current rules refuse (`connecting` with no token, `hotspot` with no described network, `online` with one) is resolved the way the next boot resolves it. Schema 2's `hotspot_password` is moved into `setup-secret` and `wpa` into `setup-security` before the record is read, so the first boot after an upgrade cannot open a network that was protected; only then is the key dropped. If the mode file itself cannot be written the boot is still protected and the next one falls back to the installer's flag. A record from a *newer* schema, one whose version never existed, or one missing a core key such as `phase`, is still refused, so a corrupt file is an error and not a silent reset. 1→3 and 2→3 are tested offline; no device has carried a record across an upgrade |
| Boot decision | `resume()`: uplink already up, or raise the setup network with a reason | partial | The [system unit and installer](../../control/setup/README.md) are installed and enabled on one Zero 2 W, and the unit has run as part of a boot, taking the online path. The access-point path has never run on a radio, and there is no image |
| Raising the setup network | An explicit NetworkManager profile this code writes (`wifi.mode=ap`, `ipv4.method=shared`, `wifi-sec.key-mgmt` of `wpa-psk` or `none`), reloaded and activated | partial | Never executed on a radio. `nmcli device wifi hotspot` was the first mechanism and is **unusable**: its manual says a password is *generated* when none is given, so it cannot express an open setup network at all, and a password-less call would have raised a WPA2 network nobody could join. The password now lives in the profile file (`0600`), never in argv; the address the profile got is what the page is bound to. The mode is read back after activation and a mismatch removes the profile. `none` is the **current default** (`DEFAULT_SETUP_SECURITY`), and the page can switch modes without a reinstall. No idle timeout, no pinned channel |
| Setup page | Real HTML/JS page, same-origin check, strict request validation | partial | Exercised only on `127.0.0.1` against the fake. The operating systems' captive-portal probe paths are answered with a redirect to the page, built from the bound address rather than the request's `Host`, but whether a phone's probe reaches the access point at all depends on the setup network's DNS, which Debra does not configure; that is unverified, and the card-note address remains the fallback. No phone has been tried. Nearby networks are scanned once, before the access point is raised, and offered in a picker; typing the name still works and is the fallback when the scan finds nothing |
| Country | The country already on the device is read with `iw reg get`; the page asks only when there is none; `raspi-config nonint do_wifi_country` sets it | partial | The read is untested on a device. On a dual-band board with no country the radio is off, so the setup network cannot start at all, and asking inside the portal is still the wrong place to ask |
| Joining | An owner-only keyfile written into NetworkManager's own profile directory, staged under a name the keyfile plugin ignores and renamed into place, pinned to the setup radio, loaded with `nmcli connection load`, activated with `connection up`, checked for a routable IPv4 address, a default route, the loaded profile being the active connection and that connection being on the setup radio, then promoted to `autoconnect=yes` | partial | Never executed. The profile check matters because a connected radio is not proof that the intended network came up — an older saved profile can win. The directory matters because a profile the keyfile plugin will not read again is not a saved network. The staging name matters because the plugin watches that directory and would parse a half-written profile. A promotion that keeps failing is a failed join, not a warning: an unsaved profile works until the next reboot and then strands the device. No DNS or HTTP probe, so a LAN with no internet is still reported as success |
| Wrong password | Setup network returns with a one-line reason; the page shows it and a retry | partial | The decision and the page are real and tested; whether `nmcli` produces that message, and how long the return takes, is unverified. nmcli's raw text is classified into one of five sentences and never shown or stored, so an error that echoes the passphrase cannot leak it |
| Attempt limits | One submission per 5 seconds, 10 attempts, then a 10-minute cooldown; a successful join resets the count | partial | The cooldown is tested offline only. The page now says to wait ten minutes, because the counter lives in the state file and a power cycle does not clear it. The note asks for 5 per 10 minutes with the limit shown in the form |
| First baseline | One owner-only archive plus manifest, captured once after the first successful join and retried on any online boot that has none | implemented | Ran once on a Zero 2 W: 8 files, 9449 bytes, `0600 root`, including both NetworkManager keyfiles. The archive and manifest are written as `.part` files and renamed, so an interrupted capture leaves nothing that looks complete, and a failure is recorded in `baseline_error` rather than silently absent. This tree also excludes the setup state directory and the access-point profile from every archive, and that exclusion has only ever run against a temporary root. Nothing restores from one |
| Finding the device afterwards | The last page names the device page URL and says what to do if it does not open | planned | No `debra-address.txt` and no mDNS announcement from this code. The address is the web prototype's port `8787`, which an image does not install |
| Re-entry | A physical input, or N boots without an uplink, raises the setup network again | partial | The [boot unit](../../control/setup/README.md) raises the setup network when the last phase was `online` and the network is not reachable. No physical input, no boot counter, no bounded hotspot window. A device that failed with no access point at all is refused a join rather than crashing the page |
| Account enrolment | First admin credential, SSH keys | planned | Nothing exists; see [N03](../roadmap.md) |
| Browser setup after onboarding | HAT and driver selection, tools and settings, update and upgrade buttons | planned | The device page has volume, mute and read-only status only; see [web control](web-control.md) |

Nothing in this table has been reviewed as a product decision, and the roadmap
packets (N02–N05, B03, WEB03/WEB05/WEB08) still own whether these parts ship.

## When the password is wrong

The sequence is deliberate, and it is the part most likely to look like a fault
to a beginner:

1. The page answers the submission **before** anything changes. That reply is the
   last thing the browser can receive over the setup network.
2. The page switches to a handover card that says, in advance, that this network
   has one radio, that the setup network has to switch off before it can join,
   that the page will disconnect, and that nothing is rebooted.
3. The setup network stops, the device associates, and success is checked
   against four things: a routable IPv4 address, a default route, the profile
   that was just loaded being the active connection, and that connection being
   on the radio the page was reached over. Association alone is not success, and
   neither is a connected radio that came up on an older saved profile.
4. On failure the setup network comes back, the same one, and the phase becomes
   `failed`. The reason is one of a small set of sentences a person can act on —
   "The Wi-Fi password was refused by the network", "That network was not
   found" — because `nmcli`'s own text is classified at the boundary and never
   shown or stored; an error that echoes the passphrase therefore cannot leak
   it. The page shows one reason and one button, and the form keeps the network
   name while clearing the password, so the one field that is probably wrong is
   empty and ready.

The device returns the setup network instead of rebooting for three reasons.
A reboot destroys the only channel that could explain the failure, so the user
is left with a device that does nothing and no message. A reboot costs another
minute or two of not knowing. And a reboot does not fix a wrong password; it only
repeats the attempt, which is why no part of this journey applies Wi-Fi by
rebooting.

The page's own copy says the setup network comes back "in about a minute". That
is page text, not a measurement; how long association plus DHCP actually takes on
each board is unmeasured.

### What the page cannot show

On one radio the setup network and the home-network association are mutually
exclusive, so the phone's connection is gone before the device has an address on
the home network. The address cannot be displayed to the person who just typed
the password, because the display channel is destroyed at exactly the moment the
address first exists. This is why the journey promises the *name* and never the
address, and why the handover card tells the user what to do next rather than
what the address will be. The
[revision 2 note](../notes/2026-11-15-wifi-onboarding-options-revision.md) sets
out the argument and the one conditional exception (a driver that advertises
access point plus client at the same time).

## What the first baseline is, and is not

It is **configuration recovery, not whole-device recovery**. One timestamped
archive and one manifest, capturing the files that make this device this device:

| Path | Why |
| --- | --- |
| `etc/NetworkManager/system-connections` | The network profiles, so the device can be put back on a network |
| `etc/hostname` | The name it answers to |
| `etc/hosts` | Not captured: the loopback alias is derived from the name, and a restore of a stale one is a device that resolves the wrong name. Applying the name rewrites it |
| `etc/timezone` | The clock's local time |
| `etc/wpa_supplicant` | Any supplicant configuration still in use |
| `var/lib/debra` | Debra's own records. The setup service's own state directory (`var/lib/debra/setup`) is **excluded**: it holds the setup-network password and the chosen mode, and neither belongs in an archived copy |

It is not a snapshot of the root filesystem, not a bootable image, not a copy of
installed packages, and not an independent backup. It lives on the same card it
describes, so it cannot repair a dead card. Restoring from it is a separate,
unproven step: no restore path exists yet (roadmap B03).

The manifest records the archive name, the creation time, the SHA-256 and byte
count, what was captured, what was skipped and why, and what was missing. A path
that is absent is recorded as missing rather than treated as an error, because a
device with no Bluetooth or no Music Assistant is normal. A file that cannot be
read is recorded as skipped and the rest of the capture still runs — a baseline
that stopped quietly at the first unreadable keyfile would look complete while
missing the one thing that matters.

**The archive contains Wi-Fi keyfiles, which are secrets.** It is created `0600`
inside a `0700` directory, and the manifest says so in its own note field. It
must never be copied into Git, a log, a support bundle, a diagnostic report, a
distributed image or a shared folder. Debra's own rule for personal recovery
points applies unchanged: they contain credentials and are never distributed.

Two more limits worth stating plainly. Nothing ever prunes these archives, so
repeated captures accumulate. And a capture that fails does not undo a working
network: the failure is logged and the device stays online.

## Trying it without a Pi

[`devserver.py`](../../control/setup/devserver.py) serves the real page and runs
the real state machine against
[`fake_nm.py`](../../control/setup/fake_nm.py), a recorded fake that answers like
NetworkManager and writes nothing to a radio. It needs no root, no `nmcli` and no
network. The commands below were run on the development laptop on 2026-11-15,
with `--state-dir` added so the state file could be read; the outputs are from
that run. The first block is the ordinary start; the failure-path block is the
one whose output is quoted.

```bash
cd /home/james/Projects/debra
python3 -B control/setup/devserver.py --port 8099
```

Open `http://127.0.0.1:8099/`. Then, to see the failure path, restart it:

```bash
python3 -B control/setup/devserver.py --port 8099 --behaviour bad-psk
curl -s http://127.0.0.1:8099/api/status
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"ssid":"HomeWiFi","psk":"wrongpassword","country":"GB"}' \
  http://127.0.0.1:8099/api/join
```

The submission is answered first, with `202`:

```text
{"status": "connecting", "ssid": "HomeWiFi", "hotspot": "Debra-Setup-demo1"}
HTTP 202
```

and a moment later the device has returned to a setup network with the reason:

```text
{"phase": "failed", "hostname": "debra-demo1", "country": "GB", "ssid": "HomeWiFi", "address": null, "last_error": "The Wi-Fi password was refused by the network", "attempts": 1, "last_attempt": "2026-11-15T22:24:03Z", "baseline": null, "baseline_error": null, "hotspot": {"interface": "wlan0", "ssid": "Debra-Setup-demo1"}, "security": "wpa", "portal": "http://10.42.0.1/", "networks": [{"ssid": "HomeWiFi", "signal": 82, "security": "WPA2"}], "updated": "2026-11-15T22:24:03Z"}
```

To look at a state directly, without clicking through it:

```bash
python3 -B control/setup/devserver.py --port 8098 --phase failed \
  --error "The password for HomeWiFi was not accepted."
python3 -B control/setup/devserver.py --port 8097 --phase online --ssid "HomeWiFi"
```

`--phase` accepts any of `unconfigured`, `hotspot`, `connecting`, `online` and
`failed`. `--behaviour` accepts `ok` (the default), `bad-psk`, `no-address`,
`no-uplink` and `scan-fails`. `--country GB` presets the country so the form
skips that question. `--error` and `--baseline-error` set the two recorded
reasons. `--state-dir` keeps the state file somewhere you can read instead of a
temporary directory under `/tmp/opencode`.

Two cautions, both from reading the code rather than from a run:

- **`--phase online` fakes the baseline.** It fills the field with a path and the
  page says "captured", but nothing was captured. `--baseline-error` sets the
  other side of that: no pointer, and a reason the page renders.
- **The dev server's baseline root is a temporary directory**, not `/`. It was
  changed after an earlier version captured the developer's own
  `/etc/NetworkManager/system-connections`. A successful join in the dev server
  therefore archives a fake tree, and no household keyfile is copied.

The offline checks behind the tables above:

```bash
python3 -B -m unittest tests.test_onboarding -v
python3 -B -m unittest tests.test_setup_identity -v
DEBRA_BROWSER_TEST=1 python3 -B -m unittest tests.test_setup_browser -v
```

266 onboarding tests, 46 installer tests, 25 identity tests and 27 browser
scenarios, all passing on 2026-11-16 against the then-current tree. They check
the decisions and the HTTP contract against the fake NetworkManager, with the
page driven in a real Chromium. They prove nothing about a radio, a real keyfile
read, or systemd.
The browser scenarios run only with `DEBRA_BROWSER_TEST=1` and an installed
Chromium, so a plain run of this suite does not drive the page at all.

## Where the code and the older notes disagree

This is the list of deltas between the requirements note and the code. The rows
marked **resolved** were closed in the code after the first draft of this page
was written; the rest are still open, so the coordinator can decide them.

| Point | [Revision 2 of the onboarding note](../notes/2026-11-15-wifi-onboarding-options-revision.md) | `control/setup/` today |
| --- | --- | --- |
| Hotspot security | WPA2 with a per-device passphrase printed on the device | **Partly resolved, unproven on a radio:** a random 12-character password, written to the boot-partition note and kept in an owner-only file, with the access point's key management and active connection read back after it is raised. It is not derivable from anything broadcast, unlike the device-name hash it replaced. A development build can be installed open (`--setup-security none`) on purpose, and that is the current default. The profile asks for `wpa-psk`, not for WPA2 specifically; whether the note is actually printed, whether a phone joins, and whether the keyfile plugin accepts an open access point are all still open |
| Trial profile and rollback | Credentials stored as a trial profile (`autoconnect=no`, retries 1), deleted on failure, old profile kept | **Resolved in code:** the profile is written into NetworkManager's own profile directory with `autoconnect=false`, activated, verified, then promoted to `autoconnect=yes`. A failed attempt deletes the profile and its file, and a promotion that keeps failing is treated as a failed join. No profile has been loaded by a real NetworkManager |
| Country | A precondition supplied at image build, because a disabled radio cannot host the portal | **Partly resolved:** the country already on the device is read first, so the question is only asked when there is none. The radio-off case is still an error |
| Success test | Four layers: associated, routable address, default route, then DNS or an HTTP probe | **Three of four:** active device, routable address and default route. No DNS or HTTP probe, so a LAN with no internet still passes |
| Finding the device | Write `debra-address.txt` to the boot partition and announce mDNS | **Partly resolved:** the card note and the page print the address the portal is actually bound to, and the operating systems' captive-portal probes are redirected to it. No `debra-address.txt`, no mDNS announcement, and whether a phone's probe arrives depends on the setup network's DNS |
| Re-entry | Physical input, or 3 boots with no uplink; a bounded hotspot window | The boot unit now raises the setup network when the last phase was `online` and the network is unreachable. Still no timer, no input, no boot counter |
| Rate limit | 5 submissions per 10 minutes, form visibly limited | **Partly resolved:** one per 5 seconds, 10 attempts, then a 10-minute cooldown instead of a permanent refusal. Still not the note's rate |
| Password field after a failure | Cleared, SSID kept | **Resolved:** the password is cleared and the network name kept |
| Passphrase handling | Hand it to NetworkManager without a copy | **Resolved in code:** written to an owner-only keyfile in NetworkManager's profile directory and loaded from there. It never appears in the commands this adapter runs (`connection load <path>`, then `connection up id <id>`), the escaping round-trips through libnm's own parser, and the setup state never holds it. It is *kept*, because deleting it left the device with no household network after a reboot |

## Open questions

- Does raising the access point from an explicit profile succeed on a fresh Pi
  OS Lite install with no country set, or does the radio refusal surface as a
  failure? Untested: no profile written by this code has ever been loaded by a
  real NetworkManager, the `reload` → `down` → `up` sequence has never re-keyed a
  live access point, and `key-mgmt=none` has never been accepted by a real
  keyfile plugin. Those four claims rest on the 1.42 manual and a double.
- The setup passphrase is now random and written to the boot partition, but is
  it actually printed or shown anywhere a person will look? A card reader on the
  Pi is not the same as a label on the case.
- Does a phone's captive-portal probe reach the access point at all? The probe
  paths are answered, but the setup network's DNS decides whether the phone asks
  them, and Debra does not configure that DNS. No phone has been tried.
- Does a phone rejoin the returning setup network by itself after a failed
  attempt, and does it stay on a network with no internet long enough to finish
  typing?
- How long does association plus DHCP actually take on each board, and therefore
  how long the "about a minute" in the page copy should be?
- Is a 10-minute cooldown after 10 failures the right recovery, or should a
  reboot clear it? Today only the clock clears it.
- What is the right check for "this network works"? A routable address is
  necessary and not sufficient; a LAN-only household with no internet is a valid
  outcome the current check cannot distinguish.
- Does the hostname actually get applied on a device? Yes: `hostnamectl
  --static` reported the new name, and the run showed the apply was only half the
  job, because `/etc/hosts` and avahi kept the old name until the next boot. The
  merged code repairs both as part of applying a name (atomic alias rewrite,
  `try-restart` of the responder), but that mechanism has not run on a board.
  Still open: does the DHCP client announce the new name, so the router's client
  list shows it?
- What does `resume()` do on a device that is deliberately offline, and should a
  device with a working Ethernet uplink stay quiet instead of raising a hotspot?
- Which parts of the baseline can actually be restored, and what does a restore
  do to a device that is currently online? No restore path exists.
- Does anything about this survive a second boot with no uplink, and is that the
  same event as the planned 3-boot re-entry rule?
