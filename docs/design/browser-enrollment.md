# Browser enrollment: how a normal person gets into the device page

**Status: the approach is decided; the implementation is not written, not
reviewed and not authorized.** James chose the enrollment path on 2026-11-15 —
see [The decision](#the-decision) below. The rest of this note is the reasoning
that led to it, kept because the rejected options will be worth reconsidering
when multi-user access and revocation arrive.
[WEB02](web-control.md#web02-address-identity-and-browser-access) names enrollment
as an open question this note answers, and no positive enrollment path may be
called implemented until it is built and reviewed.

## The problem, in one sentence

The appliance has no display and no keyboard, so a person who has just flashed a
card and joined their Wi-Fi has no way to obtain the one credential the device
page asks for — and the only current path to it is a terminal.

## The decision

James decided on 2026-11-15: **the password is chosen during setup**, on the
device's own network, behind the card-carried setup-network password. Option D
below. Nobody types a 43-character key and no unauthenticated claim window
exists on the household network.

Three development-only provisions come with it, stated by James in the same
answer:

1. until the appliance is production-ready there is a **bypass authentication**
   switch, so a person working on the page is not stopped by it;
2. there is an **uncontested "forgot password"** path, so a forgotten password
   does not mean re-flashing during development;
3. the **development password is `debra`**.

### Why those three need explicit boundaries rather than enthusiasm

Each of them is, on a shipped device, a complete takeover path. A bypass means
no credential; an uncontested reset means the credential can be replaced by
whoever asks; a well-known five-letter default means the credential is public.
That is acceptable for development on a lab network and unacceptable on a
household one, so the design must make them impossible to leave on by accident
rather than merely intended to be temporary:

- **They are service modes, never defaults.** The unit template that
  `control/web/install.py` writes must not carry any of them, and the page must
  show a permanent, unmissable banner whenever one is active — the existing
  `--auth none` banner is the model.
- **`/api/status` reports the mode**, so a script can prove what a device is
  doing without reading its journal. It already reports `auth` as `key` or
  `none`; that becomes three or four values rather than two.
- **A reset is loud.** It writes a journal line naming the event and the page
  says, in the same words, that anyone who could reach the device could have
  done it. A quiet reset is the dangerous one.
- **The weak default is refused outside development mode.** `debra` must fail
  the production rule, which means the production rule needs a minimum length
  (a proposal: 12 characters, or a passphrase rule) and the current
  `[A-Za-z0-9_-]{32,128}` shape test has to become two rules, not one.
- **One test must fail if the backdoor ships.** A production-mode server given
  the password `debra`, or asked for an unauthenticated reset, must refuse; that
  test is the thing that keeps this honest when nobody remembers this note.

The bypass itself already exists as `--auth none` and needs no new mechanism.
The reset does: the honest shape is a mode the service must have been started
with (`--development`), never a URL that works on a normally started service.

## What exists today

These are facts about the current tree, not proposals.

- The device access key is created by `init_state()` in
  `control/web/server.py`: `secrets.token_urlsafe(32)` written to
  `~/.config/debra/web/access.key`, owner-only, published by hard link so an
  existing key is never replaced. `control/web/install.py` calls it while
  preparing the service, and the server calls it again idempotently at start.
  Neither route prints the key, and `/api/status` reports only that the mode is
  `key` or `none` — never the value (`auth_mode`).
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

### Why D was chosen

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

## Where the credential would live

- One file, owned by the account that runs the device page, mode `0600`, at a
  path root can write during setup and the user service can read afterwards.
- A hash, never the password: `hashlib.scrypt` with a per-credential random salt
  and recorded parameters, stored as one line so a future parameter change is a
  version bump rather than a silent weakening. `scrypt` is in the standard
  library, so this adds no dependency to either service.
- Written by the setup service during step 1, and readable only by the page's
  account. The setup service runs as root, so it must `chown` the file rather
  than leave it root-owned — a root-owned `0600` file is a page that can never
  authenticate.
- The existing `access.key` path stays for the development and single-key modes,
  and the two must not both be silently accepted: whichever mode the service was
  started with decides which file it reads.

**Prerequisite that does not exist yet:** which account runs the device page. The
web installer is a **user** unit and installs into one user's home; the setup
service is a **system** unit and has no idea which account that is. A prepared
image would fix this (I02), and until it does, the setup service cannot write a
credential the page will read. This is the real reason the work is blocked, not
the review that currently holds the files.

## Sequencing

1. **The password chosen during setup** — the decision above.
2. **C**, with WEB02's revocation work, if a device is ever kept by more than one
   person.

The earlier draft of this note proposed shipping B first as a one-sitting change.
That is no longer the plan: it would mean building the setup screen, showing a
key, and then replacing it with a password form, and the credential store is
needed either way.

Until the work lands, the device page keeps saying what it says now — that the key
exists, that this page cannot show it, and that handing it over from a setup
screen is planned — because that sentence is currently true.

## How this would be tested without a device

Everything here is offline-fixturable:

- The setup page prompts for a password exactly once, and a reload after the join
  does not show it or any part of it.
- The password value never appears in `/api/status`, a request line, a URL, a
  journal line or a stored file; the stored file holds a hash and a salt.
- A wrong password is refused with a generic failure and no distinction that
  helps an attacker; a rejected write and a lost response are not reported as
  success.
- A password that fails the production rule is refused at setup with a message
  that says the rule, not "invalid", and `debra` is one of the refused values.
- **The development provisions cannot ship:** a production-mode server refuses
  `debra`, refuses an unauthenticated reset, and reports neither mode in
  `/api/status`; a development-mode server reports exactly which mode is active,
  and the page shows the banner. Removing any one of those checks must fail a
  named test.
- After the join, the setup network is gone and no unauthenticated endpoint
  remains on the household address.
- `control/web/install.py` never writes a unit that carries a development mode,
  and a test pins that.
- Recovery without a password is documented as it actually is. In production that
  is re-flashing; in development it is the loud reset, and the documentation must
  not describe the second as if it were the first.

None of these is a test of transport security, and none of them would prove the
page is safe on a hostile network. That remains a separate, unsolved question,
and [web control](web-control.md) already says the transport design is a
prerequisite rather than a feature.
