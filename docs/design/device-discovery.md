# Device discovery and a household overview

Status: **proposal, unimplemented.** Raised by James on 2026-11-15: the device
page should be able to find other Debra devices so he can switch between them
without knowing hostnames, and eventually apply settings to all of them.

Nothing here is approved work. It records the shape, the costs, and the parts
that would be unsafe to build first.

## What is actually being asked for

1. **Find peers.** A device page lists other Debra devices on the same network
   by name and board, without typing hostnames.
2. **Switch.** Selecting a peer opens that device's controls.
3. **Apply to all.** One action changes a setting on several devices at once.

These are three different features with three different risk levels. (1) is
cheap and read-only. (2) is mostly a browser-state problem. (3) is a fleet
management feature and should not be built until single-device configuration is
finished and reviewed.

## Finding peers

Options, cheapest first:

| Approach | Dependency | Works when | Main weakness |
| --- | --- | --- | --- |
| mDNS/DNS-SD advertisement (`_debra._tcp`) | `avahi-daemon` (already in Raspberry Pi OS) or the pure-Python `zeroconf` package | Normal home LAN; most phones and desktops already resolve `.local` | Blocked on many guest/enterprise networks; spoofable on a hostile LAN |
| UDP broadcast beacon on a fixed port | None (stdlib `socket`) | Networks that block mDNS but pass broadcast | Noisy, often blocked on Wi-Fi isolation, needs its own identity and version rules |
| Static list in a local file | None | Always | Manual, defeats the purpose as the primary method |

Recommendation: **mDNS advertisement first**, with the static list kept as an
explicit fallback. A broadcast beacon is a second choice, not a first one: it
duplicates what mDNS already solves and adds a permanently open UDP listener to
a 512 MB device.

The advertisement should carry only non-secret facts: a stable device ID, the
hostname, board model, installed release, protocol version, and the port. It
must never carry the access key, and discovery must not imply that the device is
controllable — see trust below.

A stable ID cannot be derived from `machine-id`: a fresh OS installation
generates a new one, so that hash would change exactly when the device is
re-flashed. The board serial survives reflashing and is the better input, but the
scheme is **unresolved**: collision handling, what happens on a replaced board,
and how a renamed or re-imaged device is recognised as "the same" are still open.
Whatever is chosen must be documented as an identifier, never a credential.

## Trust and keys

The current design gives each device one bearer key. Discovery must not change
that:

- Seeing a device on the network is not authorization to read or control it.
- There is no fleet key, no shared secret, and no automatic pairing.
- The browser holds each device's key separately, in the same tab storage as
  today. Switching devices means the page asks for that device's key once, then
  remembers it for the tab.
- A discovered device that answers with a different identity than the one the
  user paired with should be shown as a conflict, not silently accepted. That is
  a **labelling** check, not an authentication one: the identifier is advertised
  and copyable, and plain HTTP cannot authenticate the peer or protect the key in
  transit. A matching identity proves nothing about who answered. Only the key
  authorizes anything, and on this transport it is sent in clear.

This keeps the existing security statement true, and adds nothing to it: HTTP on
a trusted local network, one key per device, no central authority, and no claim
that discovery makes a network trustworthy.

## Applying settings to all

This is the part that can quietly damage a household. Minimum conditions before
it is built:

- Single-device configuration, status and rollback are finished and reviewed.
- Every write is previewed as a per-device diff, including devices that would be
  skipped because their board, HAT or release differs.
- A device whose state is unknown or unreachable is never written to as part of
  a bulk action.
- Bulk actions are explicit and repeatable, with a per-device result and a
  documented rollback, not a single success flag.
- No bulk action touches audio playback, volume, or anything that could produce
  sound without a deliberate per-device confirmation.

The realistic first version of "apply to all" is **apply to selected devices,
one at a time, with per-device confirmation** — which is most of the value with
much less blast radius.

## Implementation sketch

- Device side: publish `_debra._tcp` with TXT records for id, model, release,
  protocol, port. Reuse the existing metadata file; no new daemon.
- Device page: a "Devices" section that lists advertisements, marks the current
  device, and shows board/release so a mixed fleet is visible. Selecting a peer
  switches the tab's key and re-renders.
- No server-side aggregation: every device stays independent, so one device
  being off does not break the others.

## Open questions

- Whether mDNS is available on the target network at all; James's household
  network is not yet surveyed for multicast behaviour.
- Whether the Pi Zero W v1 budget tolerates an always-on avahi publisher
  alongside LVA and Sendspin. Expected cost is small but unmeasured.
- How a device should behave when two advertisements claim the same ID.
- Whether the overview belongs in this web app at all, or in Home Assistant,
  which already has a device registry and a UI.
