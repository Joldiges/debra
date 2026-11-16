# First-boot setup service

Runs `control/setup/` at boot: the device name, the Wi-Fi onboarding page and
the first baseline. **The online path has run on a device; the rest has not.**
One Zero 2 W has installed it, renamed itself from its serial, captured a
baseline, and run the unit as part of a boot
([result](../../docs/testing/results/2026-11-15-zero2w-setup-service-first-run.md)).
No radio has been raised by it, no page has been served, no join has been
performed by it, and no baseline has been restored. Read
[what is still unproven](#what-is-still-unproven) before trusting a step.

The journey itself is described in [first boot](../../docs/design/first-boot.md);
this page is only the service around it.

## What one boot looks like

The unit runs on every boot and asks `Onboarder.resume()`
([`onboarding.py`](onboarding.py)) what that boot is:

1. It gives NetworkManager up to 30 seconds to autoconnect. A configured device
   usually joins its own network in that window, and the boot is then quiet. The
   unit is ordered after cloud-init's network stage, because cloud-init owns
   `/etc/hosts` and would otherwise rewrite the alias Debra sets. That stage
   completes before `network-online.target`, so waiting for it does not wait for
   the network: naming `cloud-config.service` or `cloud-final.service` instead
   would, and `cloud-final.service` is ordered after `multi-user.target`, which
   this unit is itself wanted by.
2. `resume()` decides from the recorded state. Online means no page and no
   access point, but not a no-op boot: it re-applies the remembered device name
   through `hostnamectl`, verifies the recorded baseline and adopts or captures
   one if it is missing or damaged, and then exits 0. Because the name is
   applied unconditionally, a name changed outside Debra is changed back on the
   next boot; that is a deliberate choice. A rename on a live connection has been
   measured once: the Zero 2 W kept its `home` profile, its address and an open
   SSH session through it. A rename during a *first* boot, or one while a join is
   in flight, is still unmeasured.
3. No usable uplink: it sets the device name, looks for nearby networks while
   the radio is still free, raises the setup access point, writes the
   setup-network password to the boot partition, and serves the page on the
   address the access point actually got. In shared mode that is
   `http://10.42.0.1/`, which is also the fallback when the address cannot be
   read. The scan is a convenience for the form: a failure is an empty list and
   the person types the name. Typing accepts any printable UTF-8 name of 1–32
   octets and refuses a name that is nothing but spaces; it does not make the
   network reachable, discoverable, or compatible with the radio.
4. A submission joins the household network. The profile is written into
   NetworkManager's own store, pinned to the radio in use, and promoted to
   autoconnect only after the join is verified, so the device rejoins the
   household network on the next boot. On success the phase becomes `online`,
   the access point is gone, and the service closes the listening socket within
   a couple of seconds rather than leaving the page open. It then waits up to
   five seconds for the first baseline, because the join worker captures it
   after recording the online phase. That grace is a wait, not a deadline: the
   worker thread is deliberately not a daemon so that a capture in progress is
   not abandoned, and a slow capture therefore keeps the process alive past
   those five seconds. On failure the access point comes back with the reason
   and the page keeps serving.
5. Once the socket is bound, the note on the boot partition is reprinted with
   the address that is actually listening. The note written when the access
   point came up carries the address the radio reported, and those two are not
   always the same. A person typing an address the portal's own same-origin
   check rejects is stuck at the first step of setup.
6. After the first successful join the baseline is captured once. It is a
   **capture, not a recovery point in practice**: nothing in this repository
   restores from it, no restore has been run, and the allowlist captures
   configuration files, not a package or hardware inventory. It contains
   secrets.

Nothing reboots the device to apply Wi-Fi, and nothing restarts NetworkManager.
Applying the device name does restart `avahi-daemon` when it is running, because
that responder keeps the previous name otherwise; a responder somebody stopped is
left stopped, and a device without one publishes no `.local` name to correct.
No household passphrase is put in the setup state, passed on a command line or
kept in a log: NetworkManager's keyfile is where Debra writes it. That keyfile is
not the only copy of the secret on the device — the first baseline archives it
deliberately — and the setup network's own generated password is kept in its own
owner-only file (`setup-secret`, never in `setup.json`), served only to the reply
that asks for it, and written to the boot partition.

## Why this is a system unit, not a user unit

The [web installer](../web/README.md) uses a systemd **user** unit, because it
controls one user's audio session. This cannot, and the reasons are specific:

- `nmcli connection reload`, `nmcli connection up` and `nmcli connection delete`
  change system-wide NetworkManager state. A user unit runs with no seat and no
  login session, so polkit has nobody to authenticate and refuses. It would
  install cleanly and then fail at boot.
- `raspi-config nonint do_wifi_country` writes the supplicant configuration and
  the regulatory domain, and needs root.
- The setup page binds port 80, a privileged port.
- The baseline reads `/etc/NetworkManager/system-connections`, which is
  root-only, and writes `/var/lib/debra`.
- The setup-network note goes to the boot partition, which is owned by root.

A unit that silently fails at boot is worse than an honest system unit, so this
one is `WantedBy=multi-user.target` and runs as root.

**The tradeoff:** a root process serves an HTTP page that accepts a Wi-Fi
passphrase from whoever is on the setup network. Three things limit that, and
none of them make it a secure portal:

- The page is bound to the access point's own address rather than `0.0.0.0`.
  That is **not** ingress-interface enforcement: binding an address decides
  which address the kernel accepts requests on, not which interface a packet
  arrived from, and there is no firewall rule here. What actually keeps the page
  off the household network is that the address exists only while the access
  point does.
- In `wpa` mode the access point is `wpa-psk` with a random per-device password
  (`none` is the development default; see the mode bullet below). The password
  is written to the boot-partition note, which is how its owner learns it, and
  kept in `/var/lib/debra/setup/setup-secret` (`0600`) so the note stays true
  when the access point is raised again. While the access point is up it is also
  in that profile as `psk=` (see the file table below), and the join deletes the
  profile. It is deliberately absent from the status API, which anything that
  has joined can read; the one place it is served is the status-202 reply to any
  request that asks for `wpa` (including a repeat that only re-shows it), and
  that reply goes over cleartext HTTP to whoever has joined - while the
  network is open, to anyone in range. Anyone who can join the setup network can
  also submit the form; the password protects the setup window, not the
  household, and turning it on from an open network protects what comes after,
  not the moment of the change. The access point is raised from a profile this
  repository writes into NetworkManager's own store, so its key management is
  the one that was asked for and the password never appears in a command line.
  The profile's key management and the device's active connection are both read
  back after activation, and a mismatch takes the access point down. `nmcli
  device wifi hotspot` cannot be used for this at all, because with no password
  it generates one that nobody is shown, which is not an open network. `wpa-psk`
  is the setting; WPA2 is what NetworkManager's default `proto` makes of it,
  which this code does not pin - and all of it is unproven on a radio.
- The mode is a choice the page owns, not only the installer. It is kept in
  `/var/lib/debra/setup/setup-security` (`0600`) beside the password, deliberately
  not in `setup.json` whose schema is closed, and it wins over the installed flag
  from the first change onwards. Switching keeps the same profile: a deleted and
  recreated shared connection is handed the next subnet, which would move the
  address the page is already bound to.
- **Development mode, and today's default:** the setup network comes up open,
  with no password at all, and the page and the card note both say so. Typing a
  card password on every development boot is friction with no corresponding risk
  on a desk, so `DEFAULT_SETUP_SECURITY` in
  [`onboarding.py`](onboarding.py) is `"none"` until release planning says
  otherwise; that one line is the release decision. `--setup-security wpa`
  installs the protected mode, which stays implemented and tested, and the setup
  page can switch between them without a reinstall. The installer warns, and the
  installed flag is the mode a device starts in. Two things outrank it: a change
  on the page, whose stored choice is used from then on, and an upgrade from an
  earlier build that kept a setup password, which starts protected even under
  `--setup-security none` until somebody changes it. The boot journal says when
  the mode did not come from the flag. Never ship an image built that way.
- The service shuts the page down as soon as the device is online.

Port 80 rather than 8080 is the same kind of choice: the journey promises
`http://10.42.0.1/`, and a port suffix is one more thing a beginner has to be
told and can mistype. Root can bind it. `0.0.0.0` is not an option: the portal's
same-origin check compares the `Host` header with the address it was given, so a
wildcard bind would reject the pages it served.

## The phone should offer to open the page

Phones and laptops ask a well-known address whether they are behind a captive
portal: `/generate_204` on Android, `/hotspot-detect.html` on Apple devices,
`/connecttest.txt` and `/ncsi.txt` on Windows, `/canonical.html` on Firefox.
The portal answers each of those with a `302` to its own page, built from the
address it bound rather than from the request's `Host` header, so it cannot be
used as an open redirect. That is what makes the operating system show a "sign
in to network" sheet instead of the person having to read an address off the
card.

**Whether the probe ever arrives is unverified.** It depends on the setup
network resolving those names to the access point, which is the DNS that
NetworkManager's shared mode runs, not something Debra configures. If it does
not, the page is still reachable by typing the address from the card note, and
nothing is worse than before. On a device, this is the check:

```sh
# while the setup access point is up, from a phone or laptop joined to it
getent hosts connectivitycheck.gstatic.com   # should answer the AP address
curl -sI http://connectivitycheck.gstatic.com/generate_204 | head -3
```

A `302` with a `Location` on the setup network proves that address redirection
for that client and that request. It does not prove the operating system opened
its sign-in sheet, that every client resolves those names through the shared-mode
DNS, or that the handover and retry work afterwards.

## What the device must already have

- NetworkManager with `NetworkManager.service`, and `nmcli`.
- Python 3.10 or newer, at an absolute path.
- `iw` (the country read) and `raspi-config` (only used when a country has to be
  set). On a board with no country the radio can be off, so the country step
  fails and the access point cannot start.
- A Wi-Fi interface.
- A boot partition at `/boot/firmware` (Raspberry Pi OS Bookworm) or `/boot`.
- Root.

The installer installs no packages and changes no network setting.

## Install

On the device, from the repository root, as root:

```sh
sudo python3 -B control/setup/install.py --python "$(command -v python3)"
```

It prints the release id and path, the unit, the state directory, the card-note
path, the setup security, the retained previous unit (when upgrading) and
`changed`. It prepares files only. To make the service run at boot, after
reviewing the unit:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now debra-setup.service
```

Every start counts against the unit's `StartLimitBurst`: three starts inside five
minutes and systemd refuses the next one with "start of the service was attempted
too often". The limit exists so a failing portal cannot loop on port 80, and
maintenance trips it as readily as a fault. While working on a device:

```sh
sudo systemctl reset-failed debra-setup.service
sudo systemctl start debra-setup.service
```

`--root <directory>` prepares another tree instead of `/`; the unit it writes
still names the device paths (`/usr/local/lib/debra/setup/...`), so it is only
useful for inspection or imaging. `--restore <unit>` is the rollback below.

**`--setup-security` decides whether the setup network is open, and the default
today is `none`** - the development bypass, so the access point comes up open
with no password at all. That is a deliberate development-phase choice, not a
shipping posture: see the **Development mode** bullet under "Why this is a
system unit" above, and
`DEFAULT_SETUP_SECURITY` in [`onboarding.py`](onboarding.py), whose single line is
the release decision.

```sh
sudo python3 -B control/setup/install.py --python "$(command -v python3)" \
    --setup-security wpa
```

`--setup-security wpa` installs the protected setup network: it writes the mode
into the unit as an argument, and the service generates the random per-device
password and writes the boot-partition note on its first start. Whatever is
chosen is written into the unit as an argument, so the mode a device **starts** in is something the unit says and
not a default that a later change can reinterpret. It is not the last word on
the mode: the page can switch the running device between the two without a
reinstall, and from then on the stored choice in
`/var/lib/debra/setup/setup-security` outranks the unit's argument. A device
upgraded from a build that kept the setup password in `setup.json` also arrives
with `wpa` stored, so it starts protected even under `--setup-security none`; the
boot journal reports the mode as set on the device rather than by the flag. The
installer prints a warning when the mode is `none`.

A tree prepared from a host for a card has no running systemd to ask, so
`--enable` also creates
`/etc/systemd/system/multi-user.target.wants/debra-setup.service`. That link is
what makes the service start on the card's first boot, and nothing in this
repository does it otherwise. It refuses a unit it did not write and refuses to
replace anything already at that path. It accepts **exactly two spellings** of that
link and leaves the tree alone when one is already there: the relative
`../debra-setup.service` this installer writes, and the absolute
`/etc/systemd/system/debra-setup.service` that `systemctl enable` is documented
to write. Any other text is refused with the link untouched — an operator's link,
a link that carries the preparing host's mount point, or a damaged one. That is a
**deliberately narrow policy**, not a claim to recognise every spelling: systemd's
own manual says an administrator may add or remove enablement links by hand, so a
hand-made equivalent such as `.././debra-setup.service` is refused rather than
guessed at. The refusal is safe — the link is left exactly as it was, and the
installer writes its own spelling when the path is absent. Which exact target
bytes a real `systemctl enable` writes is still unverified, and version-scoped.

The accepted spelling is then **confirmed against the kernel**: the two paths are
compared with `os.path.samefile`, which stats them, so a component that cannot be
reached raises instead of comparing two normalized strings. Both paths are
interpreted inside the prepared tree — an absolute target is read as a path on
the device, never opened against the host's own `/etc`. This is stat-level
confirmation, not an atomic guarantee against a privileged change made between
the check and the next boot. The comparison is on the link's text and not on the
resolved destination because `realpath()` is not strict — it suppresses
resolution errors and keeps normalizing — so comparing destinations accepted
links the kernel could not open, and accepted a relative link that walked out to
the preparing host's `/` and back into the card. On a
running device, `systemctl enable` remains the right command: it also reloads
the daemon. An earlier enabled unit was booted (see the
[device result](../testing/results/2026-11-15-zero2w-setup-service-first-run.md)),
but that record does not show which command created its link or what the link's
target bytes were. It therefore establishes neither this installer's route nor a
version-specific `systemctl` spelling.

`setup.json` is migrated on read from schema 1 and from schema 2, because a
device that already ran an earlier prototype must not be left with a state file
that stops the service. Schema 2 kept the setup password inside this record; it
is moved to its own file before the record is read, and then dropped. The
migration fills the fields a later revision added (`revision`, `last_attempt`,
`attempt_token`, `attempt_claimed`, `baseline_error`), which is what makes those
an upgrade rather than a refusal. It has a floor: a record missing any field
**every** schema-1 revision wrote (the phase, hostname, country, Wi-Fi name,
address, last error, attempts, setup-network description, baseline pointer and
timestamp) is damage or a foreign file, and is refused with a message saying
so. Filling that in would turn a damaged file into an apparently unconfigured
device that raises a new setup access point. A record that is refused is left
untouched, so the evidence survives.

## The audio-HAT helper (`hat_install.py`)

This folder also holds the one program in Debra that writes the boot
configuration, because it is a device-setup action rather than a web one. It is
**not** installed by `install.py` above: it is a separate, deliberate step, and
the web installer prints the command for it.

```sh
sudo python3 -B control/setup/hat_install.py --enroll
```

Run once, by the device's owner, with a password. It writes four files and tells
systemd about two of them:

| Path | What it is |
| --- | --- |
| `/usr/local/sbin/debra-hat-install` | The helper, root-owned and executable |
| `/usr/local/lib/debra/hats.py` | The board table, the same file the page's table comes from |
| `/etc/systemd/system/debra-hat.socket` | The socket the page connects to, mode `0660`, group = the page's account |
| `/etc/systemd/system/debra-hat@.service` | One helper per connection, with the connection as stdin/stdout |

It then runs `systemctl daemon-reload` and `systemctl enable --now
debra-hat.socket`, and reports a refusal from either rather than claiming
success.

**Why a socket and not `sudo`.** The web unit ships `NoNewPrivileges=yes`, so a
setuid `sudo` cannot escalate from the service at all. Removing that line to
make `sudo` work would trade a real hardening measure for a convenience. A
socket-activated unit needs no setuid binary, so the service keeps its hardening
and the helper runs as root only for the length of one request. There is no
passwordless `sudo` rule on the device. An earlier, unreleased enrolment wrote
one; enrolment now removes that file if — and only if — its first line is
Debra's own marker.

After enrollment the page sends one JSON request down the socket:

| Request | What it does |
| --- | --- |
| `{"verb": "install", "board": "<id>"}` | Write that board's overlay line (or remove it, for `none`) |
| `{"verb": "remove"}` | Take every managed audio-HAT overlay out |
| `{"verb": "reboot"}` | Restart the device after a two-second delay, in a transient unit |

What the write does, in order: refuse an unknown board id or an unexpected field;
refuse a board whose `.dtbo` overlay or codec `.ko` this image does not carry;
copy `config.txt` to `config.txt.debra-<timestamp>` (never overwriting an
existing copy); write a temporary file in the same directory, `fsync` it, keep
the original mode, and rename it over the real file; read the file back and check
it names exactly one managed overlay and enables I2C when the board needs it; and
if that check fails, copy the backup back before reporting anything. Every line
that is not a managed overlay survives byte for byte — the graphics overlay, the
USB mode and anything added by hand.

It never reboots as part of an install. Restarting is its own verb, asked for by
its own button, after the page has confirmed with the person.

The passwordless path is exactly one connection carrying one request; the helper
takes no arguments and refuses any it is given. Tests call the functions directly
with a root path, a kernel release and a launcher, which is how the config edits
are checked without root (`tests/test_hat_install.py`).

**What enrollment does not prove:** that the codec binds, that the card survives
a reboot, or that the overlay suits a board the repository has never had in hand.
The WM8960 path has been measured on a Zero 2 W; the ReSpeaker v2 path uses the
kernel's own overlay with a codec family mismatch that is still open. The helper
refuses when the pieces are missing and says which one.

## What it writes

| Path on device | Mode | Purpose |
| --- | --- | --- |
| `/usr/local/lib/debra/setup/releases/<sha256>/` | `0700` | Fixed payload, content-addressed; old releases retained |
| `/usr/local/lib/debra/setup/previous-units/` | `0700` | Previous generated units, retained for rollback |
| `/var/lib/debra/setup/setup.json` | `0600` | The setup state; no household passphrase and no setup-network password |
| `/var/lib/debra/setup/setup-secret` | `0600` | The setup-network password, so a re-raised access point matches the note |
| `/var/lib/debra/setup/setup-security` | `0600` | The mode in force (`wpa` or `none`); one word, read at every start. Written by the page, or carried forward from a `wpa` in an upgraded record |
| `/var/lib/debra/setup/baseline/` | `0700` | Baseline archive and manifest; contains secrets. The baseline excludes this whole directory, so the setup password and the chosen mode are in **no** baseline archive |
| `/etc/NetworkManager/system-connections/debra-setup.nmconnection` | `0600` | The setup access point's profile. In `wpa` mode this is a **second copy of the setup password** (`psk=`) for as long as the access point exists; the join deletes it, and it is excluded from every baseline |
| `/etc/NetworkManager/system-connections/<id>.nmconnection` | `0600` | The household Wi-Fi profile, written by the join and kept; this is where the passphrase is written (the baseline below archives a copy) |
| `/etc/hosts` | (kept) | The loopback alias line, rewritten to the device's name so `hostname -f` and `sudo` resolve it. Replaced atomically, keeping the file's owner and mode; every other line keeps its text. cloud-init rewrites this file too, which is why the unit is ordered after it |
| `/etc/systemd/system/debra-setup.service` | `0644` | The rendered unit; no credential |
| `/etc/systemd/system/multi-user.target.wants/debra-setup.service` | (link) | Only with `--enable`: a link to the unit (relative, or the absolute spelling systemd is documented to write), which starts it at the next boot |
| `/boot/firmware/debra-setup.txt` | (boot partition) | Setup-network name and password, written at runtime |

`debra-setup.service` in this directory is the **template**: the installer
substitutes `@PYTHON@`, `@RUNNER@`, `@STATE@`, `@CARD_NOTE@` and `@SECURITY@`
with systemd-quoted values. It is copied into the release as well, so a re-install
from a release works. The release also contains `install.py` itself, because the
unit runs `releases/<id>/install.py --serve`; the runner on the device is
therefore this reviewed file and not a generated second program.

An identical install changes nothing and creates no rollback copy. They are not
treated alike: a **release** that differs from what the installer would write is
refused, and so is one whose content address is already used by different bytes.
A **unit** that differs is snapshotted to `previous-units/<stamp>.service`
and then replaced, because updating the unit is the whole reason the install
path exists; `--restore <unit>` puts the retained copy back atomically. Nothing
is ever deleted.

## Check that it worked

```sh
systemctl status debra-setup.service
journalctl -u debra-setup -b --no-pager
sudo systemctl show debra-setup.service -p ExecStart -p MainPID
sudo cat /var/lib/debra/setup/setup.json
ss -ltn 'sport = :80'
```

- On a device that is already online the unit is `inactive (dead)` with
  `status=0/SUCCESS`. That is the expected result, not a failure: it found a
  usable uplink, so no page and no access point. It did re-apply the remembered
  device name and re-checked the baseline before exiting; the journal says
  `setup phase online`.
- On a device with no uplink the journal says `setup phase hotspot` and
  `setup page listening on http://<address>/`, naming the address it bound. The
  card note on the boot partition holds the setup-network name and password.
- `ExecStart` must name the `releases/<id>/install.py` that the installer just
  reported. `MainPID` and `ps -p <pid> -o args=` must show the same path.
- After the device is online, `ss` must show nothing listening on port 80. The
  unit's `ExecStart` is the only thing that ever binds it.

## Roll back

An upgrade keeps the unit it replaced. Use the exact `previous_unit` path that
install printed, not an arbitrary newest file:

```sh
sudo python3 -B control/setup/install.py --restore '<previous_unit>'
sudo systemctl daemon-reload
sudo systemctl restart debra-setup.service
```

The restore is a temp file plus an atomic rename, not `cp`: a copy interrupted
partway leaves a truncated unit that cannot start. The old release is retained,
so the restored unit still names real code. `--restore` refuses a file that is
not a unit this installer wrote and is not under `previous-units/`.

To stop the service without removing anything:

```sh
sudo systemctl disable --now debra-setup.service
```

This is **setup-service rollback**, not whole-device recovery. Speech, music and
the web prototype are unaffected; they are separate units.

## What is still unproven

One device run has happened, on the other line's tree: the Zero 2 W installed
and ran `control/setup/` at `a90cfba`, then rebooted with the unit enabled,
recorded in
[the first-run result](../../docs/testing/results/2026-11-15-zero2w-setup-service-first-run.md).
It exercised the online path, the hardware-derived rename, a baseline over a real
root, the unit being started by systemd, and then a boot. The run found two
defects — `/etc/hosts` and `avahi-daemon` keeping the old name until the next
boot — and `set_hostname` now repairs both, so the fix is here even though the
run was not.

What the run does not cover is this tree's own code: that tree archived
`setup.json` where this one excludes the whole state directory, and its identity
apply was the draft the atomic rewrite later replaced. The list below is what
this tree has not run; where the run has moved an item, the item says so. Not all
of what is left is about a radio - it also includes the baseline exclusion list,
the identity fix's atomic write, a boot partition that is not mounted, the unit
as systemd renders it, and a cooldown that is words rather than a countdown.

Ordered by how likely it is to bite on a real first boot.

1. **The Wi-Fi profile has never been loaded by a real NetworkManager.** The
   profile is written into `/etc/NetworkManager/system-connections` and loaded
   from there, because a keyfile anywhere else is not one the keyfile plugin
   will read again after a reboot. That the plugin accepts this file, that the
   profile survives a reboot, and that `connection modify ... autoconnect yes`
   takes effect are all untested. A profile that is not promoted leaves the
   device with no network at all on the next boot, so the join treats a failed
   promotion as a failed join and brings the setup network back.
2. **The portal's bind address is read from NetworkManager, with a fallback.**
   It asks for the access point interface's IPv4 and binds that, falling back to
   `10.42.0.1` when the read returns nothing. If the bind fails, the access
   point is taken back down and the phase is recorded as `failed`, so the device
   does not sit there offering a network with no page — but the person then has
   neither a page nor a setup network, and needs a console. Neither path has run
   against a real radio, and the listener is not rebound if a recreated access
   point lands on a different subnet.
3. **The 30-second uplink wait is a guess.** If NetworkManager takes longer than
   that to autoconnect on a slow card, a configured device raises a setup access
   point, and the household connection may not come up until the next boot. Two
   boots have been timed and both joined well inside the window; a boot with a
   slow autoconnect has not been observed.
4. **Only Wi-Fi uplinks count.** `nmcli`-based `active()` looks at Wi-Fi devices,
   so a device with working Ethernet and no Wi-Fi still raises the setup access
   point.
5. **A real root has been archived once, by a tree that archived more than this
   one does.** The device run captured the two NetworkManager keyfiles (`0600`,
   `missing: []`), and its manifest says the archive holds the household
   passphrase. That tree did not exclude the setup state directory; this branch
   does, and that exclusion has still only ever run against a temporary root.
6. **The device name has been applied, but never chosen by a first boot.** One
   Zero 2 W was renamed `debra-lab` → `debra-8518d6` on a live connection
   without losing it, a later boot re-applied the same name, and the run also
   forced a rename and reverted it. What has not happened is a device choosing
   its name on its first boot, or the shipped atomic write running on a board. The adapter refuses a
   name that would not resolve as `<name>.local`, rewrites the `/etc/hosts` alias
   and restarts the mDNS responder. Unproven: a rename performed by a *first*
   boot, where the name changes at the moment the device is deciding its own
   identity, and whether ordering after cloud-init is enough on an image whose
   metadata pins a hostname. The board verified the *behaviour* — alias repaired,
   `hostname -f` and `sudo` correct, `<name>.local` answering — with an earlier
   draft that wrote the file in place and restarted the responder only on a
   change; the atomic replace and the unconditional reconcile were added after
   review and are covered offline only.
7. **The captive-portal redirect may never be asked for.** The probe paths are
   answered, but the setup network's DNS decides whether a phone reaches them;
   see [above](#the-phone-should-offer-to-open-the-page). Until that is measured
   on a phone, the card-note address is the reliable route.
8. **The network scan has never run against a radio.** It is issued once, before
   the access point is raised, because a scan with the access point up can drop
   the person's phone off it. Whether that window is clean on a real driver, and
   how long the scan takes, is untested. A failed or slow scan is not fatal, but
   it does delay the page appearing.
9. **If `/boot/firmware` is not mounted when the note is written**, the note is
   created on the root filesystem instead, where the person holding the card
   cannot see it. The service warns (`The setup note is not on a mounted boot
   partition`) and the access point still starts. Nothing refuses to run without
   that partition, and no boot has been tried with it absent.
10. **The unit has run, and `systemd-analyze verify` passes on it — once.** One
    Zero 2 W has loaded it at boot, and verify accepted the installed unit for
    release `b72a508c…` ([result](../../docs/testing/results/2026-11-15-zero2w-setup-service-first-run.md)).
    That is one rendering on one image: nothing here proves polkit, D-Bus, a radio,
    or the same line on an image whose cloud-init units are named differently.
11. **The cooldown is words, not a countdown.** The page says to wait ten
    minutes because the attempt counter lives in the state file and a power
    cycle does not clear it. There is no retry-after the page can count down.
12. **The access point has never been raised from a written keyfile, in either
    mode.** `nmcli device wifi hotspot` cannot make an open network (with no
    password it invents one nobody is shown), so the access point is instead a
    keyfile this repository writes: `mode=ap`, `ipv4.method=shared`, and
    `key-mgmt` either `wpa-psk` with the stored password or `none` for the open
    development mode. It is then loaded with `nmcli connection reload`, taken
    down if it is already active, brought up, and read back through the profile
    and `device show`. None of that has run on a radio, so neither the open mode
    nor the protected one is demonstrated, and the read-back that is supposed to
    catch a mismatch has never had a mismatch to catch. Switching modes cycles
    that same profile rather than deleting and recreating it, which is also
    unexercised.

## How the risky steps are kept small

These are the decisions that the tests defend, and the reasons they exist:

- **The page is answered before the radio is touched.** A submission reserves
  the attempt, writes the `202`, and only then does a worker stop the access
  point and associate. The reply is the last thing that can travel over the
  setup network. If the reply cannot be written at all — the phone dropped —
  the reservation is released, so the device is not left `connecting` for ever.
- **A reservation is identified by a token, not by a network name.** The same
  network can be retried with a corrected password, so the name cannot say which
  attempt a worker belongs to. The token is random because the timestamp beside
  it has one-second resolution.
- **Success means the profile that was just loaded is the active connection**,
  on the radio the page was reached over, with a routable address and a default
  route. A connected radio is not proof of any of that.
- **The country is set after the access point is down.** It is a radio change,
  and doing it before the reply could disrupt the only channel the person has.
- **A failed attempt tries to delete its profile and its file**, so a wrong
  password does not leave a second profile competing with the household network.
  This is best effort: a deletion that fails is suppressed and logged, there is
  no retry and no crash recovery, and no real NetworkManager has been asked to
  clean up after a failure here. Treat "no competing profile" as the intent, not
  as a guarantee.
- **A baseline is published, not overwritten.** Each file is written under a
  name nothing reads, flushed, and linked into place; `os.link` refuses to
  replace an existing file, and the manifest is published last. A same-second
  retry gets a suffix instead of overwriting. A capture never archives its own
  directory, a file is read whole before it is added to the archive, and
  `latest()` only returns a manifest whose archive still hashes to what it says.
- **The setup page prints the address it is served on**, not `<hostname>.local`:
  the same-origin check admits only that address, and the `.local` name returned
  `403`.

The offline checks behind this page:

```sh
python3 -B -m unittest tests.test_setup_install -v
python3 -B -m unittest tests.test_onboarding -v
python3 -B -m unittest tests.test_setup_identity -v
DEBRA_BROWSER_TEST=1 python3 -B -m unittest tests.test_setup_browser -v
```

They check the artifacts on disk, the boot decisions, and the page's own
behaviour in a real browser, all against a recorded fake NetworkManager. They do
not prove anything about a radio, a real keyfile read, systemd, or hardware. The
browser cases need an already-installed Chromium and are opt-in, so a plain run
does not exercise the page at all.

Guards in this subsystem have been checked by breaking them and watching a test
fail, but that is evidence about the guards that were broken, not a proof of the
whole subsystem. Each round's transforms, the failing test for each, and any
survivors are recorded in that round's verdict under `.local/reviews/`
(the newest file under `.local/reviews/setup-ap-20261115/` is the current one
for this branch; the `setup-r6-20261115/` and `setup-r8-20261115/` verdicts
belong to the earlier, independent setup work); a survivor is a test gap, not a
harmless change. Earlier rounds found guards that no test covered at the
time.
