# First boot: from a flashed card to a working device

**Status: partly implemented, 2026-11-15. Nothing here has run on a device.**

The phase machine, the setup page and the first baseline exist as code under
`control/setup/` and pass offline tests against a recorded fake NetworkManager.
No radio has been raised, no `nmcli`, `hostnamectl` or `raspi-config` call has
been executed by Debra, no card has been flashed, and the setup service has
never been enabled at boot. Its system unit and installer now exist and are
tested offline — see [the setup service](../../control/setup/README.md). Read
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
3. On a phone, join that network and open the setup page. Today the page is
   served at `http://10.42.0.1/` and nothing prints that address for you yet.
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
| `unconfigured` | No state file exists yet, so a blank record is returned and written on first change | `schema: 1`, an empty hostname, every other field null, `attempts: 0` |
| `hotspot` | `resume()` finds no routable Wi-Fi uplink, or a fresh start; also what a failed attempt falls back to | `phase`, `hotspot: {ssid, interface}`, `last_error: null` |
| `connecting` | A submission was accepted by the page and the worker entered `join()` | `phase`, `ssid`, `attempts` incremented, `last_error: null` |
| `online` | The adapter returned a Wi-Fi device with a routable IPv4 address | `phase`, `ssid`, `address`, `hotspot: null`, and `baseline` once the capture succeeds |
| `failed` | The join raised; the setup network could not be raised; or a boot found the device was `online`/`connecting` and is not now | `phase`, a one-line `last_error`, and the `hotspot` record when the setup network came back |

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
| Applying the name | `hostnamectl`-equivalent call so the running system uses it | partial | The NetworkManager adapter has no `set_hostname` at all. The recorded name is not applied; the code logs "recorded but not applied" and carries on |
| State across reboots | Closed JSON schema, atomic owner-only writes, refuses unknown keys and phases | implemented | Nothing on the schema; corruption handling is an error by design |
| Boot decision | `resume()`: uplink already up, or raise the setup network with a reason | partial | The [system unit and installer](../../control/setup/README.md) exist and are tested offline. Neither has been enabled or started on a device, and there is no image |
| Raising the setup network | `nmcli device wifi hotspot` with a fixed profile name and a password derived from the device name | partial | Never executed on a radio. The password is written to `debra-setup.txt` on the boot partition so it can be printed and read, and it is never stored in the setup state. No idle timeout, no pinned channel |
| Setup page | Real HTML/JS page, same-origin check, strict request validation | partial | Exercised only on `127.0.0.1` against the fake. No captive-portal helper, so no phone will offer to open it; the address is in the boot-partition note, but no phone has been tried |
| Country | The country already on the device is read with `iw reg get`; the page asks only when there is none; `raspi-config nonint do_wifi_country` sets it | partial | The read is untested on a device. On a dual-band board with no country the radio is off, so the setup network cannot start at all, and asking inside the portal is still the wrong place to ask |
| Joining | A private keyfile loaded with `nmcli connection load`, activated with `connection up`, then checked for an active device, a routable IPv4 address and a default route | partial | Never executed. No DNS or HTTP probe, so a LAN with no internet is still reported as success |
| Wrong password | Setup network returns with a one-line reason; the page shows it and a retry | partial | The decision and the page are real and tested; whether `nmcli` produces that message, and how long the return takes, is unverified |
| Attempt limits | One submission per 5 seconds, 10 attempts, then a 10-minute cooldown; a successful join resets the count | partial | The cooldown is tested offline only. The note asks for 5 per 10 minutes with the limit shown in the form |
| First baseline | One owner-only archive plus manifest, captured once after the first successful join | implemented | The capture code is real and tested against a temporary root. It has never run on a Pi with real keyfiles |
| Finding the device afterwards | The last page names the device page URL and says what to do if it does not open | planned | No `debra-address.txt` and no mDNS announcement from this code. The address is the web prototype's port `8787`, which an image does not install |
| Re-entry | A physical input, or N boots without an uplink, raises the setup network again | partial | The [boot unit](../../control/setup/README.md) raises the setup network when the last phase was `online` and the network is not reachable. No physical input, no boot counter, no bounded hotspot window |
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
3. The setup network stops, the device associates, and success is checked: an
   activated profile with a routable IPv4 address. Association alone is not
   success.
4. On failure the setup network comes back, the same one, and the phase becomes
   `failed` with a short reason from `nmcli` — for example "Secrets were
   required, but not provided." The page then shows one reason and one button,
   and the form keeps the network name while clearing the password, so the one
   field that is probably wrong is empty and ready.

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
| `etc/timezone` | The clock's local time |
| `etc/wpa_supplicant` | Any supplicant configuration still in use |
| `var/lib/debra` | Debra's own records, including this setup state |

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
{"phase": "failed", "hostname": "debra-demo1", "country": "GB", "ssid": "HomeWiFi", "address": null, "last_error": "Secrets were required, but not provided.", "attempts": 1, "last_attempt": "2026-11-15T22:24:03Z", "baseline": null, "hotspot": {"interface": "wlan0", "ssid": "Debra-Setup-demo1", "password": "debra-0f887027"}, "portal": "http://debra-demo1.local/", "updated": "2026-11-15T22:24:03Z"}
```

To look at a state directly, without clicking through it:

```bash
python3 -B control/setup/devserver.py --port 8098 --phase failed \
  --error "The password for HomeWiFi was not accepted."
python3 -B control/setup/devserver.py --port 8097 --phase online --ssid "HomeWiFi"
```

`--phase` accepts any of `unconfigured`, `hotspot`, `connecting`, `online` and
`failed`. `--behaviour` accepts `ok` (the default), `bad-psk`, `no-address` and
`no-uplink`. `--country GB` presets the country so the form skips that question.
`--state-dir` keeps the state file somewhere you can read instead of a temporary
directory under `/tmp/opencode`.

Three cautions, all from reading the code rather than from a run:

- **`--phase online` fakes the baseline.** It fills the field with a path and the
  page says "captured", but nothing was captured.
- **The `portal` field is not an address.** The status response reports
  `http://wlan0/`, which is the interface name in the host position. Nothing on
  the page uses it, but it would mislead anything that did.
- **A successful join in the dev server captures the host's real configuration.**
  The baseline step calls the real capture with `/` as its root, so on a laptop
  with real NetworkManager profiles it copies those keyfiles into an owner-only
  archive under the state directory. That is why the success behaviour was not
  run on this laptop: `/etc/NetworkManager/system-connections` here holds real
  household profiles. If you do run it, delete the state directory afterwards.

The offline checks behind the tables above:

```bash
python3 -B -m unittest tests.test_onboarding -v
```

30 tests, all passing on 2026-11-15. They prove the decisions and the HTTP
contract against the fake; they prove nothing about a radio.

## Where the code and the older notes disagree

This is the list of deltas between the requirements note and the code. The rows
marked **resolved** were closed in the code after the first draft of this page
was written; the rest are still open, so the coordinator can decide them.

| Point | [Revision 2 of the onboarding note](../notes/2026-11-15-wifi-onboarding-options-revision.md) | `control/setup/` today |
| --- | --- | --- |
| Hotspot security | WPA2 with a per-device passphrase printed on the device | **Resolved in code:** the passphrase is derived from the device name and written to the boot-partition note. Whether the note is actually printed is still open |
| Trial profile and rollback | Credentials stored as a trial profile (`autoconnect=no`, retries 1), deleted on failure, old profile kept | `nmcli device wifi connect` creates and activates an ordinary autoconnecting profile; nothing is removed on failure and no previous profile is protected |
| Country | A precondition supplied at image build, because a disabled radio cannot host the portal | **Partly resolved:** the country already on the device is read first, so the question is only asked when there is none. The radio-off case is still an error |
| Success test | Four layers: associated, routable address, default route, then DNS or an HTTP probe | **Three of four:** active device, routable address and default route. No DNS or HTTP probe, so a LAN with no internet still passes |
| Finding the device | Write `debra-address.txt` to the boot partition and announce mDNS | Neither; the page prints a `.local:8787` URL and no announcement is made by this code |
| Re-entry | Physical input, or 3 boots with no uplink; a bounded hotspot window | The boot unit now raises the setup network when the last phase was `online` and the network is unreachable. Still no timer, no input, no boot counter |
| Rate limit | 5 submissions per 10 minutes, form visibly limited | **Partly resolved:** one per 5 seconds, 10 attempts, then a 10-minute cooldown instead of a permanent refusal. Still not the note's rate |
| Password field after a failure | Cleared, SSID kept | **Resolved:** the password is cleared and the network name kept |
| Passphrase handling | Hand it to NetworkManager without a copy | **Resolved:** written to an owner-only keyfile, loaded with `nmcli connection load`, then deleted. It never appears in argv, and a test asserts that |

## Open questions

- Does `nmcli device wifi hotspot` succeed on a fresh Pi OS Lite install with no
  country set, or does the radio refusal surface as a hotspot failure? Untested.
- The setup passphrase is now derived and written to the boot partition, but is
  it actually printed or shown anywhere a person will look? A card reader on the
  Pi is not the same as a label on the case.
- Does the page need a captive-portal helper to be found at all, or is typing
  `10.42.0.1` acceptable for a beginner? No phone has been tried.
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
- Does the hostname actually get applied on a device, given that the adapter has
  no `set_hostname`, and does the DHCP client then announce it so the router's
  client list shows it?
- What does `resume()` do on a device that is deliberately offline, and should a
  device with a working Ethernet uplink stay quiet instead of raising a hotspot?
- Which parts of the baseline can actually be restored, and what does a restore
  do to a device that is currently online? No restore path exists.
- Does anything about this survive a second boot with no uplink, and is that the
  same event as the planned 3-boot re-entry rule?
