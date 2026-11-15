---
title: How a Debra satellite should report its own health to Home Assistant
date: 2026-11-15
type: project-learning
status: unreviewed
task: none (coordinator-assigned desk research)
author: OpenCode subagent
author_model: deepseek/deepseek-v4.1-flash-1017
author_variant: unknown
sources:
  - Home Assistant 2026.11.1, MQTT integration — https://www.home-assistant.io/integrations/mqtt/ (checked 2026-11-15)
  - Home Assistant 2026.11.1, MQTT sensor — https://www.home-assistant.io/integrations/sensor.mqtt/ (checked 2026-11-15)
  - Home Assistant 2026.11.1, REST API (developer docs) — https://developers.home-assistant.io/docs/api/rest/ (checked 2026-11-15)
  - Home Assistant 2026.11.1, authentication API (long-lived tokens) — https://developers.home-assistant.io/docs/auth_api/ (checked 2026-11-15)
  - Home Assistant 2026.11.1, Webhook trigger — https://www.home-assistant.io/integrations/webhook/ (checked 2026-11-15)
  - Home Assistant 2026.11.1, People and user configuration — https://www.home-assistant.io/docs/configuration/user-configuration/ (checked 2026-11-15)
  - Home Assistant 2026.11.1, State object — https://www.home-assistant.io/docs/configuration/state_object/ (checked 2026-11-15)
  - Home Assistant 2026.11.1, RESTful integration — https://www.home-assistant.io/integrations/rest/ (checked 2026-11-15)
  - Home Assistant 2026.11.1, RESTful sensor — https://www.home-assistant.io/integrations/sensor.rest/ (checked 2026-11-15)
  - Home Assistant core, rest/entity.py and rest/data.py (dev branch) — https://github.com/home-assistant/core/blob/dev/homeassistant/components/rest/entity.py (checked 2026-11-15)
  - Home Assistant apps, Mosquitto broker DOCS.md (master) — https://github.com/home-assistant/apps/blob/master/mosquitto/DOCS.md (checked 2026-11-15)
  - mosquitto.conf(5), Debian bookworm packaged man page — https://manpages.debian.org/bookworm/mosquitto/mosquitto.conf.5.en.html (checked 2026-11-15)
  - OASIS MQTT 3.1.1 specification, OS — https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html (checked 2026-11-15)
supersedes: []
---

## Summary

Desk study only: no Home Assistant, Music Assistant, broker or Debra device was
contacted, and nothing was installed. There are **no `tested` claims**. "Must not
run a broker" is taken as a requirement; the earlier note already settled that
([earlier note](2026-11-15-optional-network-services.md), `D`).

The documented answer is that **MQTT as a client is the only route in this set
that gives Home Assistant an automatic "this device is gone" signal, with a
credential whose blast radius can be bounded by the broker** — provided the
household broker has per-client users and ACLs. The satellite holds a username,
a password and its own topic prefix; it holds no broker. `D` for every mechanism,
`U` for the Debra wiring.

The other routes are weaker on exactly the point the task asks about:
Home Assistant's REST state push needs an **administrator** token, a 10-year
secret, and still leaves a frozen value rather than an "offline" one (`D`);
a webhook needs no token at all but creates no entity and **cannot report its own
failure** (`D`); letting Home Assistant poll the device's own HTTP service gives
correct availability and leaves no Home Assistant secret on the device, but
reverses the direction of trust and needs no broker only because it needs no
push (`D`).

Smallest credential on a coin-sized, physically reachable device: **nothing on
the device** if Home Assistant polls it; among push routes, a **webhook ID**
(smallest secret, capability limited to one automation, but no availability),
then a **broker user restricted by ACL** (small secret, bounded to one topic
tree, keeps availability), and last an **administrator long-lived token**
(everything the user can do, for ten years).

This **confirms and sharpens** the earlier note's recommendation; it does not
reverse it. See §5.

Labels per [evidence](../evidence.md): `D` = upstream-documented (a primary
page or the project's own source), `R` = third-party report, `U` = unknown or
inference, `tested` = a named Debra test record. Source keys `[HA-…]` are
defined with full URLs in the register at the end.

## 1. What each route needs on the satellite

| Route | Device holds | Authentication | What Home Assistant shows when reporting stops | Ev. |
| --- | --- | --- | --- | --- |
| MQTT client + will + availability topic | broker host/port, username, password, its own topic prefix. No broker | Broker login; with the official Mosquitto app that is a Home Assistant user, and the app "does not support anonymous logins" | Entity becomes `unavailable`; last values remain as attributes | `D` |
| MQTT client, no availability, no `expire_after` | same | same | Last value persists and looks live; retained values are replayed after a Home Assistant restart | `D` |
| REST state push (`POST /api/states/<id>`) | a long-lived access token | Bearer token; **Admin** for this endpoint | State freezes at the last POST; no offline marking is documented | `D` |
| REST action call (`POST /api/services/…`) | a long-lived access token | Bearer token; not marked Admin | Whatever the action set (e.g. an `input_boolean`) stays as last set; no timeout | `D`,`U` |
| Webhook (`/api/webhook/<id>`) | a webhook ID string | None — "A webhook doesn't need a password or a token" | Nothing is created or updated by the call itself; only an automation run/trace | `D` |
| Home Assistant polls the device's own HTTP service | no Home Assistant secret; may hold credentials for its own endpoint | Home Assistant authenticates *to* the device (basic/digest, optional) | Entity becomes `unavailable` after a timeout or connection error | `D` |
| Ping (reachability only) | nothing | none | Device tracker goes `not_home` after `consider_home` (default 180 s) | `D` |

### MQTT as a client

The device does not need a broker; it needs a login on the household one. The
official Mosquitto app's own documentation says to "create individual users for
each of your clients and create an appropriate ACL" and shows the `customize` +
`acl_file` route for a topic ACL file `[MOSQ-APP]`. Mosquitto's `acl_file`
supports `topic [read|write|readwrite|deny] <topic>`, `user <username>`, and
`pattern … %u` substitution, and `allow_anonymous` defaults to false
`[MOSQ-CONF]`. The Home Assistant MQTT integration generates and keeps secret the
credentials it uses for itself, which is a separate account from the satellite's
`[HA-MQTT]`.

Home Assistant documents the failure signal directly: "A device or service can
announce its availability by publishing a Birth message and set a Will message at
the broker. When the device or service loses connection to the broker, the
broker will publish the Will message. This allows the MQTT integration to make an
entity unavailable." `[HA-MQTT]` The MQTT 3.1.1 specification lists the triggering
cases including "The Client fails to communicate within the Keep Alive time", and
that timeout is one and a half times the keep-alive period `[MQTT-SPEC]`.

Two documented traps:

- **Clean shutdown.** The same Home Assistant page says the will "will be sent
  both in case of a clean disconnect … and in case of an unclean disconnect"
  `[HA-MQTT]`, while MQTT 3.1.1 says the will is published "unless the Will
  Message has been deleted by the Server on receipt of a DISCONNECT Packet"
  `[MQTT-SPEC]`. The two can be reconciled (Home Assistant is describing its own
  client), but which applies to a device is `U`. Design so the satellite
  publishes `offline` itself before exiting, and treat the will as the
  crash-and-power-loss path.
- **Discovery replay.** "When MQTT starts up, all existing MQTT devices, entities,
  tags, and device triggers, will be unavailable until a discovery message is
  received and processed" `[HA-MQTT]`. A device that only publishes discovery at
  boot will show unavailable after every Home Assistant restart unless it
  subscribes to the birth message or publishes retained discovery.

Refinement over the earlier note: it said a Debra "may be an MQTT *client*"
(`D` there). The credential consequence — a per-device broker user plus a topic
ACL, not one shared login — is documented in `[MOSQ-APP]` and missing from that
note.

### Home Assistant REST push

`POST /api/states/<entity_id>` is documented as "**Admin**. Creates or replaces a
state", and warns: "This only changes what Home Assistant shows. It does not talk
to the device, and the next update of the entity overwrites it" `[HA-REST-API]`.
`POST /api/events/<event_type>` is also Admin. `POST /api/services/<domain>/<service>`
is not marked Admin, so a restricted user can call actions but cannot write
states `[HA-REST-API]`.

Every request needs a bearer token; for a script that is a long-lived access
token created on the profile `[HA-REST-API]`, and those "are valid for 10 years,
and are used exactly like an access token" `[HA-AUTH-API]`. Home Assistant
documents two user levels — administrators, and non-administrators who "cannot
reach the configuration and system settings" `[HA-USERS]` — and explicitly names
"A service or integration account that authenticates with the API" as a reason to
have a user without a person `[HA-USERS]`. No token *scoping* is documented
anywhere I read; a token's reach is the user's reach (`U` for anything finer).

That combination is the problem for a cheap device: reporting a *state* needs an
administrator, and an administrator's token on a £10–40 board in a room is the
largest secret in this comparison.

Two smaller variants are possible and worth stating because they are what "its
own service calls" can mean:

- **Call an action** (e.g. `input_boolean.turn_on`) with a non-admin token, then
  let a Home Assistant automation turn it off when the value goes stale. This
  works but the liveness logic is entirely on the Home Assistant side; the
  entity has no timeout of its own (`D` for the endpoint, `U` for the design).
- **Let Home Assistant call the device** (the device's own service). Covered
  below as polling.

### Webhook

The webhook trigger is documented as the way "another app or service" starts an
automation, addressed as `/api/webhook/<id>`, with `local_only` defaulting to
true and methods defaulting to POST and PUT `[HA-WEBHOOK]`. Security is stated
plainly: "A webhook doesn't need a password or a token. Anyone who knows the
webhook ID can send a request to it" and "Treat the ID like a password"
`[HA-WEBHOOK]`.

The decisive limitation for health reporting is the response behaviour: "Home
Assistant almost always answers a webhook request with 200 OK, so that nobody can
find out whether a webhook ID exists. It also answers 200 OK when the webhook ID
doesn't exist, or when a request from outside your local network reaches a
webhook that only accepts local requests" `[HA-WEBHOOK]`. A satellite therefore
cannot tell a correct webhook ID from a wrong one, from a firewall block, or from
a rotated ID. Errors on the device side are invisible.

### Home Assistant polling the device

The RESTful sensor fetches a URL the device already serves, with `scan_interval`
defaulting to 30 s and `timeout` defaulting to 10 s: "If the timeout is reached,
the sensor will become unavailable" `[HA-REST-SENSOR]`. The integration also
exposes an `availability` template option `[HA-REST]`.

The source confirms the broader case beyond timeout: `RestEntity.available`
returns false when `self.rest.data is None`, and `RestData.async_update` sets
`data = None` on both `TimeoutError` and `aiohttp.ClientError` (connection
refused, DNS failure) `[CORE-REST-ENTITY]`, `[CORE-REST-DATA]`. So a dead device
yields `unavailable`, not a stale number — which is exactly the semantic the
other push routes lack. This is source-level evidence, not prose documentation.

## 2. Availability semantics: stale versus missing

Home Assistant's own vocabulary is precise `[HA-STATE]`:

- `unavailable`: "The entity cannot provide its state right now."
- `unknown`: "The entity has no value for its state."
- `last_updated`: when state or attributes last changed; `last_changed`: when the
  state last changed.

Applied to each route:

| Route | Stops reporting → | Distinguishable from live? | Ev. |
| --- | --- | --- | --- |
| MQTT + availability | `unavailable` within the keep-alive bound (≤1.5× keep-alive after a silent loss; promptly when TCP closes) | Yes, by state; history shows the last real value then the gap | `D` |
| MQTT + `expire_after: N` | `unavailable` N seconds after the last message | Yes; documented as the backstop when a will cannot fire | `D` |
| MQTT, neither | last value, indefinitely ("By default, the sensor's state never expires") | **No** — a frozen value is indistinguishable without comparing `last_updated` | `D` |
| REST state push | frozen value; `last_updated` stops advancing | Only by automation on `last_updated`; no offline state documented | `D`,`U` |
| REST action call | last action result persists | Only by a bespoke timeout automation | `D`,`U` |
| Webhook | nothing changes at all | **No** — absence is invisible; no entity exists | `D` |
| Polling | `unavailable` on timeout or client error | Yes | `D` |
| Ping | `not_home` after `consider_home` | Yes, but it measures reachability, not health | `D` |

"Missing" only really happens on the webhook route, and there it is total: no
entity, no device, no state — the only trace is an automation's last-triggered
time. Every other route leaves a stale *something*, and the question becomes
whether that something is labelled `unavailable`.

Two further documented cautions:

- Retained MQTT state is replayed after a restart, so "the sensor [can] become
  available with an expired state"; the docs recommend not retaining sensor
  state `[HA-MQTT-SENSOR]`. Home Assistant calculates the remaining expiry itself.
- Triggers: "Most triggers that have an entity as the target do not react when an
  entity transitions from an unavailable or unknown state" `[HA-TRIGGER]`.
  An offline notification must use a state trigger on `to: unavailable`, not a
  device trigger.
- `availability_mode` (`all`/`any`/`latest`, default `latest`) lets a device
  combine a process-alive topic and a link topic `[HA-MQTT]`.
- `expire_after` is a per-entity setting; the unit is seconds and 0 means never
  `[HA-MQTT-SENSOR]`.

## 3. Which leaves the smallest credential

Assuming the threat the task names — a cheap board in a room that someone can
pick up and read the flash — the relevant question is not secret length but
*capability if the secret is copied*.

| Secret on the device | What a copier gains | Bound by | Revoke | Ev. |
| --- | --- | --- | --- | --- |
| None (Home Assistant polls) | Nothing on the Home Assistant side; they can read the device's own endpoint | Direction of trust | n/a | `D`,`U` |
| Webhook ID | Trigger one named automation, nothing else | That automation's actions | Change the automation's ID | `D` |
| Broker username + password | Publish/subscribe inside its ACL; with `topic readwrite debra/<id>/#` only that tree | Mosquitto ACL | Change the broker password for that user | `D` |
| Long-lived access token | Everything that Home Assistant user may do, for 10 years; Admin if created by an admin | The user's role only | Delete the token on the profile | `D` |

Ranking for Debra:

1. **No credential at all** is smallest, and polling achieves it — but it makes
   the device a listener that Home Assistant must reach, and any LAN peer can
   read the endpoint unless the device adds its own auth. It also inverts the
   failure story: when the device is dead, Home Assistant notices; when Home
   Assistant is dead, the device does not care. (`U` for Debra specifics.)
2. **Webhook ID** is the smallest *pushed* secret and the most tightly bounded,
   but §1 and §2 show it buys no availability signal and cannot detect its own
   misconfiguration. That is a poor trade for a health channel, whose whole job
   is to be trustworthy when things break.
3. **Broker user with ACL** is the smallest secret that still delivers automatic
   unavailability. It is one username and one password, revocable per device, and
   the damage is confined to the device's own topic tree. This is the
   recommendation.
4. **Long-lived token** is the one to avoid on device hardware. A stolen satellite
   would hand over a ten-year credential with the user's full authority; if the
   state-push endpoint is used, that authority is administrator.

Mitigations that are ordinary practice rather than documented here: keep the
credential out of the image, generate it at onboarding, store it root-only
(`0600`), and never reuse one across devices (`U` — not a documentation claim).

## 4. What Home Assistant documents for self-diagnostics without a custom integration

- **MQTT discovery.** A device publishes a configuration topic and a JSON
  payload; Home Assistant creates the entities and a device registry entry with
  `identifiers`, `manufacturer`, `model` and so on `[HA-MQTT]`. No integration
  code is needed. Sensor entities can be marked `entity_category: diagnostic`
  `[HA-MQTT-SENSOR]`, and discovery keys can be abbreviated specifically "to
  conserve memory when sending a discovery message from memory constrained
  devices" `[HA-MQTT]`. Shared root options, including availability, apply to
  every component of a device `[HA-MQTT]`.
- **RESTful sensor against an endpoint the device already serves.** This is the
  shortest path from Debra's existing web health page to Home Assistant entities,
  with `json_attributes` for the individual readings `[HA-REST]`.
- **Glances integration.** Documented as monitoring "the system information
  provided by the Glances API" on a remote host, requiring "a running instance of
  glances in Web Server Mode" `[HA-GLANCE]`. A device can therefore report CPU,
  memory, disk and load through a packaged agent plus a first-party integration,
  with no custom code.
- **System Bridge integration.** "An application that runs on your local machine
  to share system information via its API/WebSocket"; setup requires the app's
  token, and it is auto-discoverable `[HA-SYSBRIDGE]`.
- **Ping.** Reachability only, with `consider_home` and `scan_interval`
  `[HA-PING]`; useful as a second signal, not as health.
- **Not this:** the Diagnostics platform is for integration authors to let users
  download a config entry's or device's data — it requires a `diagnostics.py`
  `[HA-DIAG]`. It is not a generic device-health channel.
- **ESPHome native API.** Home Assistant keeps a persistent connection and
  reconnects automatically `[HA-ESP]`, which sounds ideal, but the page does not
  state what happens to entities while the device is away (`U`), and it presumes
  ESPHome firmware or a compatible protocol rather than a Python satellite.

## 5. Relation to the earlier note

[Optional network services](2026-11-15-optional-network-services.md) listed
"Debra health → HA (proposal, no new daemon)" as: "Reuse the existing
web/diagnostic data; publish as HA entities or MQTT", maintainer "Debra itself",
cost "nearly zero", impact "Only this device's telemetry pauses", verdict
"Image", evidence `U`. Its recommendation 3 says to "Make each Debra report its
own health, and let HA hold the dashboard", marked `U` for the proposal and `D`
for Home Assistant owning availability, notifications and history. Its exclusion
list says "MQTT broker: no … A Debra may be an MQTT *client*; it must not be the
broker".

**My findings do not change that recommendation.** They fill in what the earlier
note left as "entities or MQTT", which its own text treats as interchangeable and
which are not:

- The two differ in availability: only MQTT gives an automatic `unavailable`.
  "Entities" written by REST need an administrator token and still leave a
  frozen value.
- The earlier note does not mention that a satellite login needs a **per-device
  broker user and an ACL**; without that, one shared MQTT login makes every
  satellite equivalent, and a stolen device can publish into any topic.
- The earlier note's phrase "availability handling and an MQTT broker are needed
  for that route" appears in
  [optional sensors](2026-11-15-optional-sensors-and-front-panel.md) and reads as
  if the broker were a device cost. It is a household cost; the device holds a
  client login.

So: same verdict (`Image`, device reports, Home Assistant displays, no new
daemon, no broker on the satellite), with the transport now specified and one
new requirement added. It is a refinement, not a correction, so no superseding
note is warranted.

## 6. Open questions and blocked sources

- **Does a non-administrator Home Assistant user authenticate successfully to
  the Mosquitto app, and does `acl_file` apply to Home Assistant-auth users as it
  does to `logins` entries?** `U`. The app docs recommend per-client users but do
  not say which user class.
- **Does a state created with `POST /api/states` survive a Home Assistant
  restart?** `U`. The docs describe creation and overwriting, not persistence;
  nothing documents restoration of a state with no integration behind it.
- **Is there any device-level "offline" indication, as opposed to per-entity
  `unavailable`?** `U`. Availability is documented per MQTT entity.
- **Timeout or `unknown`?** When the device answers but the template yields
  nothing, whether the entity is `unknown` or `unavailable` was not established
  `U`; the two are documented as different states `[HA-STATE]`.
- **Does `expire_after` fire when the publishing process is stopped (SIGSTOP)
  but its TCP connection stays open?** `U`; the will certainly does not fire.
- **Blocked:** `https://mosquitto.org/man/mosquitto-conf-5.html` refused
  connections during this session; the Debian-packaged man page was used instead
  and is the source of the ACL quotes. `https://developers.home-assistant.io/docs/api/webhook/`
  redirected to the contributors' home page (no such page), so the user-facing
  webhook trigger page is cited.
- **Not checked:** whether the household even runs an MQTT broker. If it does
  not, adding one is a household decision covered by the earlier note, and
  polling is the broker-free fallback.

## 7. Smallest experiment that would settle the open question

The most valuable unknown is the pair in §6 that decides the recommendation:
whether a restricted broker user really is confined by an ACL, and whether Home
Assistant turns the entity `unavailable` on both a killed process and a stopped
one. The smallest test that answers both without touching the household:

1. On one scratch host (not the household Home Assistant), run a throwaway
   Mosquitto container and a throwaway Home Assistant container, with MQTT
   discovery enabled.
2. Create one broker user with ACL `topic readwrite debra/test/#`, add it as a
   non-administrator Home Assistant user, and add the MQTT integration using
   that user.
3. On one Debra (the lab Pi 5 is the authorized device), run a short script that
   publishes one discovery payload plus an availability topic, then a state every
   30 s.
4. Three runs: `kill -9` (expect the will → `unavailable`), graceful `SIGTERM`
   with an explicit offline publish (expect `unavailable`), and `kill -STOP`
   (record whether only `expire_after` catches it).
5. Try publishing to `debra/other/#` with the same credential (expect refusal).

**What it leaves behind on the device:** one root-only (`0600`) credential file
holding a test-only broker username and password, one systemd unit, and one log
line per publish. Nothing on the household broker or Home Assistant. The test
broker keeps retained discovery and availability messages until its container is
removed. Rollback is deleting the unit, the credential file and the container —
the credential is throwaway, so no rotation is needed.

## Source register

| Key | Full URL | Used for |
| --- | --- | --- |
| `[HA-MQTT]` | https://www.home-assistant.io/integrations/mqtt/ | Birth/will, availability, discovery, device registry, abbreviations, secrets |
| `[HA-MQTT-SENSOR]` | https://www.home-assistant.io/integrations/sensor.mqtt/ | `expire_after`, retained-state warning, `entity_category` |
| `[HA-REST-API]` | https://developers.home-assistant.io/docs/api/rest/ | Bearer auth, Admin markers, state/action/event endpoints |
| `[HA-AUTH-API]` | https://developers.home-assistant.io/docs/auth_api/ | Long-lived token lifetime and use |
| `[HA-WEBHOOK]` | https://www.home-assistant.io/integrations/webhook/ | Webhook ID, `local_only`, 200 OK behaviour |
| `[HA-USERS]` | https://www.home-assistant.io/docs/configuration/user-configuration/ | Admin vs non-admin, service accounts, local-only |
| `[HA-STATE]` | https://www.home-assistant.io/docs/configuration/state_object/ | `unavailable` vs `unknown`, `last_updated` |
| `[HA-REST]` | https://www.home-assistant.io/integrations/rest/ | RESTful polling, `scan_interval`, `availability` |
| `[HA-REST-SENSOR]` | https://www.home-assistant.io/integrations/sensor.rest/ | `timeout` → unavailable, polling default |
| `[CORE-REST-ENTITY]` | https://github.com/home-assistant/core/blob/dev/homeassistant/components/rest/entity.py | Availability on failed update |
| `[CORE-REST-DATA]` | https://github.com/home-assistant/core/blob/dev/homeassistant/components/rest/data.py | `data = None` on timeout/client error |
| `[HA-PING]` | https://www.home-assistant.io/integrations/ping/ | `consider_home`, reachability only |
| `[HA-GLANCE]` | https://www.home-assistant.io/integrations/glances/ | Remote host metrics via Glances |
| `[HA-SYSBRIDGE]` | https://www.home-assistant.io/integrations/system_bridge/ | Agent + token + integration |
| `[HA-ESP]` | https://www.home-assistant.io/integrations/esphome/ | Persistent connection, auto-reconnect |
| `[HA-DIAG]` | https://developers.home-assistant.io/docs/core/integration/diagnostics/ | Diagnostics need integration code |
| `[HA-TRIGGER]` | https://www.home-assistant.io/docs/automation/trigger/ | Triggers and unavailable states |
| `[MOSQ-APP]` | https://github.com/home-assistant/apps/blob/master/mosquitto/DOCS.md | No anonymous logins, per-client users, ACL setup |
| `[MOSQ-CONF]` | https://manpages.debian.org/bookworm/mosquitto/mosquitto.conf.5.en.html | `acl_file`, `pattern`, `allow_anonymous` default |
| `[MQTT-SPEC]` | https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html | Will publication conditions, keep-alive |
| `[EARLIER]` | docs/notes/2026-11-15-optional-network-services.md | Prior recommendation |
| `[SENSORS]` | docs/notes/2026-11-15-optional-sensors-and-front-panel.md | Earlier "broker needed" phrasing |
| `[WEB]` | docs/design/web-control.md | The health data Debra already collects |

Evidence tally: 0 `tested`, 0 `R`. Everything above is `D` (primary documentation
or the project's own source) or `U` (inference, configuration-dependent, or not
covered by any page I could read). No third-party summary was relied on.
