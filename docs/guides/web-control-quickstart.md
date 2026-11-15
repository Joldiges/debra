# Debra web controls: the short version

**Status, 2026-11-15.** A prototype, not security-reviewed, and the current code
candidate is not approved ([roadmap](../roadmap.md#browser-first-device-control)).
This page says what the two pages do today; the
[design document](../design/web-control.md) describes much more than exists.

## 1. What each page is for

| Page | Use it for |
| --- | --- |
| `http://127.0.0.1:8787/` | The hub: lists Debra devices and links to each; served by the development computer, so it works only there. |
| `http://debra-3c6b3f.local:8787/` | The lab Pi 5's own page: its status, speaker volume and mute. |

Open the hub to find a device; open a device page to read or change it. Both pages
are one app ([index.html](../../control/web/assets/index.html)); the hub also gets a
device list with `--devices` ([README](../../control/web/README.md)), and its
volume card controls the computer running it.

## 2. Opening them

- **Hub.** On the development computer, open `http://127.0.0.1:8787/`. Loopback
  only, so another machine's browser cannot use it.
- **Devices find the hub on their own.** A device that advertises `_debra._tcp`
  appears in the list labelled **Discovered**, without anyone editing a file; a
  device from the `--devices` file is labelled **Configured**. Discovery only
  decides what the hub lists: it is an announcement, not a login, so the device
  still has to accept you when you follow the link.
- **Device.** Open `http://debra-3c6b3f.local:8787/`. A `.local` name is mDNS: it
  needs an mDNS-capable resolver on the computer you browse from and a device
  that is advertising. Whether a given computer resolves it is unknown here;
  failure is ordinary, and is not proof the device is down.
- **If the name fails, use the IP:** `http://<device-ip>:8787/`. The server
  answers only the host names it was installed with, so this needs that IP passed
  with `--host` at install time ([README](../../control/web/README.md) step 3).
  Whether the lab Pi currently allows its IP is unknown here.
- **A device missing from the hub list** means discovery found nothing: a failed,
  empty or timed-out scan clears discovered entries, and the configured list
  still shows ([README](../../control/web/README.md)). If `avahi-browse` is not
  installed on the hub's computer, discovery silently shows nothing at all.

## 3. The volume control

From [app.js](../../control/web/assets/app.js), which is what the browser runs.

- **Moving the slider changes nothing on the device.** It holds a preview,
  labelled "… % · not applied", and a status refresh will not overwrite it.
- **Apply volume** sends one write to the explicit native sink and links its
  channels. Percent is a control setting, not loudness and not a safety limit.
- **Mute is a separate button and a separate write**, so a successful mute cannot
  hide a failed volume change.
- **No sound plays on load.** The page only fetches status: no test tone and no
  playback in `app.js`, and no write on load, refresh or reconnect.
- **An unanswered write stays unconfirmed** until a fresh reading matches what
  you asked for; it is not assumed, and not silently retried.
- **Status refreshes every 3 seconds**, so an external change appears by itself.

## 4. What `--auth none` means

From `python3 control/web/server.py --help` (defined in `control/web/server.py`):

```text
  --auth {key,none}     key: require the device access key (default); none:
                        development bypass, no authentication at all
```

Bluntly: with `--auth none`, anyone who can reach port 8787 on that machine can
read its status and change its volume and mute. No key, no password, no prompt.
Host and same-origin checks still run, but they stop a web page from cross-siting
the server, not a person, script or other computer on the network. Plain HTTP
also lets the network read and alter traffic ([README](../../control/web/README.md)).

The page says so on its welcome card, offering "Continue without a key
(development)" for that tab only. The device is recorded as deployed this way on
2026-11-15 ([update log](../updates/2026-11-15.md)); I cannot confirm it still is.

To switch to key mode, install again without `--auth none` (the default is key)
and restart the service. Quoted from [README](../../control/web/README.md) steps 3
and 4; these belong on the device, not the development computer:

```sh
python3 -B control/web/install.py \
  --sink 'alsa_output.REPLACE_WITH_REAL_SINK' \
  --bind 0.0.0.0 --port 8787 \
  --host debra-example.local:8787
systemctl --user daemon-reload
systemctl --user restart debra-web.service
systemctl --user is-active debra-web.service
```

`debra-example.local` is a placeholder; use the device's real names. Then read the
access key on the device as README step 5 describes; never share it.

## 5. What the page does not do yet

From the packet list in the [design document](../design/web-control.md): each row
is a requirement, not a feature, and none is built. Neither page installs,
updates, restarts or reconfigures anything; the hub links, it does not control.

| Packet | Not built |
| --- | --- |
| WEB02 | Wi-Fi onboarding, hardware-derived identity, browser enrollment or revocation, secure transport. Access is one shared key. |
| WEB03 | Choosing a board or HAT, driver and overlay state, compatibility, reboot requirements. You see device-tree strings and optional retained labels. |
| WEB04 | Installed, configured, connected and working state, versions and prerequisites. You get systemd unit found/active/enabled only; the Bluetooth proxy and Music Assistant server are not inspected. |
| WEB05, WEB06 | Voice and music settings, pairing, duck/pause/resume; LED profiles and button mapping. |
| WEB07 | Observation times and freshness, CPU-core voltage, zswap pool and hit/reject counters, storage used and total. Storage shows free space only. |
| WEB08 | Updates, component install and removal, logs and diagnostic export, backup and restore. |

## 6. Honest limits

- **No security review.** No reviewed threat model, TLS, key rotation or
  multi-user access ([README](../../control/web/README.md)); trusted local network
  only, no port-forwarding or tunnel.
- **Prototype, awaiting acceptance.** The code review returned changes requested
  and the candidate is not approved
  ([roadmap](../roadmap.md#browser-first-device-control)).
- **Deployment evidence disagrees.** [Getting started](getting-started.md) says web
  deployment is not recorded; the update log describes a lab install. Read the
  device instead.
- **Install with the installer, not by copying.** It copies a fixed set of
  runtime files and refuses modified releases and unmanaged services
  ([README](../../control/web/README.md)); editing a release is unsupported.
- **Tests prove less than they look.** They are offline and synthetic-Chromium
  checks; they do not establish physical audio quality, ARMv6 support or safety
  against a hostile network.
