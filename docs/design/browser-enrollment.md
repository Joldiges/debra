# Browser enrollment: how a normal person gets into the device page

**Status: proposal, 2026-11-15. Unreviewed, unimplemented and unapproved.** This
is a design note, not a decision and not an authorization. Nothing here is
blocked on missing evidence; it is blocked on a choice, and the choice is
James's. [WEB02](web-control.md#web02-address-identity-and-browser-access) already
names enrollment as the open question this note is trying to answer.

## The problem, in one sentence

The appliance has no display and no keyboard, so a person who has just flashed a
card and joined their Wi-Fi has no way to obtain the one credential the device
page asks for — and the only current path to it is a terminal.

## What exists today

These are facts about the current tree, not proposals.

- The device access key is created on the service's **first start**, by
  `init_state()` in `control/web/server.py`: `secrets.token_urlsafe(32)` written
  to `~/.config/debra/web/access.key`, owner-only, published by hard link so an
  existing key is never replaced. Neither the installer nor the page prints it,
  and `/api/status` reports only that the mode is `key` or `none` — never the
  value (`auth_mode`).
- The page asks for it once per browser tab and keeps it in that tab; the server
  compares an `Authorization: Bearer …` header with `hmac.compare_digest`.
- The [quickstart](../../control/web/README.md) retrieves the key by reading that
  file in a private terminal on the device. That is a terminal, and the
  [project brief](../project-brief.md) rules a terminal out of ordinary
  supported setup. The README also documents an optional `/#key=…` fragment
  enrollment and then discourages it, because copying such a link exposes the
  key; no enrollment design should rely on it.
- The setup service stores its **own** generated password for its setup access
  point in the setup state, serves it to the setup page, and writes it into the
  card note on the boot partition (`control/setup/README.md`). Nothing connects
  that password to the device page's key.
- The device page and the setup page are separate services with separate
  installers: a systemd **user** unit for the page and a systemd **system** unit
  for setup. Neither installer installs the other, and neither service knows
  whether the other is present.

So today there are three credentials or none, depending on what was installed:
a setup-network password on the card, an access key on the device, and no path
from one to the other.

## Constraints any option has to meet

- No universal key or password shipped in an image
  ([web control](web-control.md) WEB02).
- No SSH or terminal for ordinary setup (project brief).
- Must work with no cloud account and no internet, because the device page is
  the local control surface.
- Plain HTTP on a home network is not confidential against a hostile peer; the
  design must not imply it protects the credential
  ([web control](web-control.md) WEB02, "must never happen").
- The credential must not appear in a URL, a log, a status payload or the
  device's own page after it has been set.
- Revocation and multi-user access are WEB02 work. A single shared credential is
  the prototype's model and remains a gap, not a feature.

## The four options

| Option | How the person gets in | What protects the first moment | Cost |
| --- | --- | --- | --- |
| **A. Claim window** | The first browser to reach the device page sets a password; the window closes permanently on success or after a timeout | Nothing but reachability, on the household network, until someone claims it | Small; standard practice (Home Assistant does this) |
| **B. Show the key once** | The setup page, after a verified join, displays the generated key once with a copy button; the person pastes it into the device page | The setup network's own password, carried on the card | Small: the setup service reads or creates the same key file |
| **C. Approve from Home Assistant** | The device page says "approve this device in Home Assistant"; HA shows a six-digit code that the person types | The household's existing HA login | Largest: an HA integration, a device↔HA channel and a code exchange |
| **D. Choose the password during setup** | Step 1 of setup asks for a device password, on the setup network only, before the join; the device page accepts it afterwards | The setup network's own password, carried on the card — and no window exists on the household network at all | Small to medium: a credential store both services share |

### Why D is the recommended end state

D is B with a person-chosen value and one extra property: the moment when a
credential can be set exists **only** while the device is on its own access
point, whose password is on the card. That is the same bootstrap the setup page
already relies on, so it adds no new trust boundary and no unauthenticated
window on the home LAN — which A does have, for as long as it takes the owner to
get to a browser.

It also fixes the failure mode that matters most: a 43-character random key is
not something a person will type into a phone successfully, and a key they must
copy between two local pages is a support burden on exactly the person this
project is for. "Pick a password for this device" is a thing people already
know how to do.

The honest caveats are real and must be in the page's own words:

- The password crosses plain HTTP **inside** the setup access point. Anyone who
  is on that network and can read the traffic can read the password. The setup
  network is WPA2 with a per-device password, and the page is only up while the
  device is unconfigured, but that is a limit, not a security proof.
- It is a local control credential, not an account. It must not be a password the
  person reuses, and the page should say so.
- One password, one authority: anybody with it is an administrator, and there is
  no per-browser revocation. That is WEB02 work.
- Losing it without SSH is unsolved. Today the only honest answer is "re-flash the
  card and start again", and that must be written down rather than discovered.

### Why B is worth building first anyway

B needs almost nothing that does not exist: the setup service would read
`state/access.key` if present, show it once on the final screen with the address
to open, and never show it again. It removes the terminal from the journey in a
change small enough to review in one sitting, and it is useful whether or not D
is ever adopted.

D then replaces B's display with a form and a shared credential file; B's screen
is not wasted work, it is the same screen with a different body.

### Why C is the better multi-user answer, later

Six-digit HA pairing gives per-device approval, revocation in a place the person
already understands, and no shared secret at all. It is also the only option
that answers "who else may control this device". It is not the first thing to
build because it makes the local page depend on HA being reachable and on an
integration that does not exist, and the device is already an HA client — a
failed pairing would leave no local way in.

## Sequencing

1. **B**, as soon as the setup service and the web installer can be installed as
   a pair. Precondition: something installs both, which is image work (I02), not
   a UI change.
2. **D**, replacing B's screen, once there is a credential store both services
   read (`/var/lib/debra/…`, mode `0600`, hashed with a memory-hard KDF).
3. **C**, with WEB02's revocation work, for a device more than one person keeps.

Until the pairing question is settled, the device page keeps saying what it says
now — that the key exists, that this page cannot show it, and that handing it
over from a setup screen is planned — because that sentence is currently true.

## How this would be tested without a device

Everything here is offline-fixturable:

- The setup page shows the key or prompts for a password exactly once, and a
  reload after the join shows neither.
- The key value never appears in `/api/status`, a request line, a URL or the
  journal, in either mode.
- A wrong password is refused with a generic failure and no distinction that
  helps an attacker; a rejected write and a lost response are not reported as
  success.
- With the claim window design, a second claim after success is refused, and the
  window closes on the declared condition; a claim that fails part way leaves
  the device unclaimed, not half-claimed.
- After the join, the setup network is gone and no unauthenticated endpoint
  remains on the household address.
- Recovery instructions exist for the "password forgotten" case and say
  re-flashing, if that is what they say.

None of these is a test of transport security, and none of them would prove the
page is safe on a hostile network. That remains a separate, unsolved question,
and [web control](web-control.md) already says the transport design is a
prerequisite rather than a feature.
