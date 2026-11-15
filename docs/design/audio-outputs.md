# Audio outputs: choosing, and playing to all of them

> **Historical design exploration, not current instructions.** The conclusions
> below include superseded/unsupported claims. Read
> [the correction note](../notes/2026-11-15-audio-and-enclosure-corrections.md)
> first. The headphone tap remains unverified; no `debra-audio` CLI exists;
> announcement fan-out is a proposal, not an adopted default. Native browser
> volume uses [one explicitly selected sink](../../control/web/README.md).
> Tone/microphone measurements do not prove speech level, safety or inaudibility.
> The experiments below **did generate sound**; do not repeat them under the
> current silent-investigation constraint.
> The earlier power-fault description is historical; James reports improvement
> after changing the supply.

James asked for this on 2026-11-15: *"the user should be able to easily select
which outputs it runs on — or maybe even on 'all' at once such that any one
plugged in will be had."*

**Requirement and design options, not implemented behaviour.** `T` means a
linked device test record; `reported` identifies historical observations without
such a record. Proposals and unknowns are not proven behavior.

## "Output" means three different things

Most confusion about audio outputs comes from collapsing these. They are
independent, and each needs its own setting.

| Layer | What it is | On the lab Pi today |
| --- | --- | --- |
| **Codec taps** | One sound card, several physical output pins on the codec: line out, headphone out, composite out; independent gains are a design consideration | `T` — the [path test](../testing/results/2026-11-15-lab-pi5-silence-and-hang.md) found the speaker on **line out**. Jack routing is `unknown`; no headphones were plugged in |
| **Sinks** | PipeWire nodes for outputs such as the HAT, HDMI or a USB DAC | `reported` — this page's historical observation below says HDMI 0 appeared even without a display; HDMI 1 did not. No linked result record confirms it |
| **Network players** | Sendspin and Snapcast: the music goes out over the network to a player, which is a different transport entirely | `T` — Sendspin 9.1.0 streamed to the HAT sink in the [lab result](../testing/results/2026-11-15-lab-pi5-lva-sendspin.md) |

A user who says "play on the speaker or the TV" is usually talking about layer 2.
A user who says "and my headphones too" may be talking about layer 1, depending
on the jack's routing. A user asking "why does music go to the other room" is
talking about layer 3.

## The finding that changes the design

The [path test](../testing/results/2026-11-15-lab-pi5-silence-and-hang.md)
supports the speaker being fed from the codec's **line output** through the
board's TPA2005D1 amplifier (`tested`, one specimen). Which tap feeds the 3.5 mm
jack remains `unknown`: nothing was plugged into it. With PipeWire stopped, a
1 kHz tone was played to each path in turn and recorded by the HAT's own
microphone:

| Path | Microphone at 1 kHz |
| --- | --- |
| `HP` (headphone tap; jack routing unverified) | ≈ −100 dBFS, near the noise floor — no headphones were plugged in |
| `HPCOM` (composite) | nothing, ≈ −90 dBFS |
| `Line` (the speaker) | **−21 dBFS** |

Two consequences:

- **"Correct mixer, no sound" is a real state.** Every service was active, the
  sink existed at 65 %, and the device was silent because `Line DAC` was at zero
  gain. The mixer script sets it; the *stored* `alsactl` state had drifted, and a
  state saved before the script ran survives every reboot. Check the line gain
  before anything else, and note that `HP DAC` is not the speaker's control.
- **The codec taps are plausibly an "all" switch — unverified.** Enabling `Line`
  and `HP` at sane gains *should* make a plugged-in headphone work without
  software noticing, which would be the cheapest half of what James asked for.
  Nothing has been plugged into the jack on this HAT, so the routing is a
  hypothesis, not a fact. The mixer script writes `0dB` for the headphone tap;
  what the device stored was raw `0`, and those two have not been shown to be the
  same setting — see
  [the correction note](../notes/2026-11-15-audio-and-enclosure-corrections.md).

## Layer 2: one sink, or all of them

| Option | How | Good | Bad |
| --- | --- | --- | --- |
| **One selected sink** | Set the PipeWire default sink to the user's choice | Simplest, no drift, works with any player | Nothing else plays; the user has to know the name |
| **Combine sink** | A virtual sink intended to fan out to several real sinks | Proposed "all at once" for announcements; one setting | Independent clocks may drift; each member has its own volume; output presence and hotplug behavior are unverified |
| **Default follows hotplug** | `module-switch-on-connect`: a newly connected device becomes the default | Plug in a TV, sound goes there | It *moves* the audio instead of adding it, so a plugged-in monitor silently steals the voice reply — exactly the failure the pinned `AUDIO_OUTPUT_DEVICE` was added to prevent |

A combine sink with a single-sink option was proposed, not adopted. Whether an
unplugged member is harmless, and how hotplug affects replies, remain unverified;
see [the correction note](../notes/2026-11-15-audio-and-enclosure-corrections.md).

### Proposed boundary for the combine sink

Music is a proposed exclusion: Sendspin and Snapcast synchronize players, but
fan-out to sinks with independent clocks may undermine that synchronization.
Neither the effect nor the following split has been tested or adopted:

- **Voice, announcements, timers, chimes → the combine sink:** proposed fan-out.
- **Music → one sink, chosen by the user:** proposed way to avoid local fan-out.

That split matches the existing product decision that duck/resume and pause/resume
are a user setting, and it is the same boundary `M04` describes as
"exclusive/shared audio ownership".

## What the user should actually touch

A small, boring **proposed** interface; these commands do not exist:

```
debra-audio outputs                 # list what exists, what is connected, what is active
debra-audio outputs set speaker     # the HAT
debra-audio outputs set hdmi        # whichever HDMI port has a display
debra-audio outputs set all         # combine: everything currently present
debra-audio outputs follow on|off   # whether a newly plugged device becomes active
```

Proposed underneath: a config file with the chosen profile, a systemd user unit
that applies it at boot and on device change, and manual recovery using
`pactl`/`wpctl`. The goal is no hidden state: the config would say what should
be true, and `debra-audio outputs` would report what is true.

## What is not settled

- **Whether the 3.5 mm jack is on the line tap or the headphone tap.** The
  speaker is on line; the jack is untested. If the jack is also on line, codec
  routing may not separate speaker and headphones. A future check would require
  plugging in headphones and testing each tap; that audible test is not currently
  authorized.
- **Volume behaviour in a combine sink.** The historical observation below
  `reports` a 17.7 dB reduction at 50 % and suggests a second cubic attenuator.
  There is no linked test record establishing that conclusion; hardware volume
  interaction and general behavior are `unknown`.
- **Bluetooth.** Not considered at all. It is a sink like any other in
  principle, and it has its own latency and reconnect problems.
- **Whether the user wants music to follow the announcement profile.** Separate
  profiles are a proposal, not an adopted decision.

## Historical lab observations reported 2026-11-15

The following are `reported` observations by this historical page's original
author (identity not recorded), not `tested` results: there is no linked result
record for the combine-sink, echo-cancel or HDMI checks. A tone was played; its
recorded microphone level does not establish that it was inaudible or safe. See
the [correction note](../notes/2026-11-15-audio-and-enclosure-corrections.md) and
the [evidence audit](../notes/2026-11-15-evidence-claim-audit.md).

| Question | Answer |
| --- | --- |
| Is `module-combine-stream` available? | `reported`: `libpipewire-module-combine-stream.so` was present on PipeWire 1.4.2. Presence alone does not demonstrate a usable native combine sink |
| Is `module-echo-cancel` available? | `reported`: `libpipewire-module-echo-cancel.so` was present. Presence alone does not demonstrate echo cancellation |
| Do HDMI sinks appear with no display connected? | `reported`: HDMI **0** appeared in `SUSPENDED` state with neither display connected; HDMI **1** did not |
| Does a combine sink work, and does audio reach the speaker through it? | `reported`: `pactl load-module module-combine-sink sink_name=debra_test slaves=<HAT sink>` returned a module id; a tone played with `pw-play --target debra_test` registered −40.4 dBFS at the microphone, versus −40.6 dBFS directly to the member. This is not a linked test result or proof of general unity gain |
| Does the combine sink's own volume do what a user expects? | `reported`: reducing 100 % to 50 % cost 17.7 dB; 35 % cost 26.7 dB. A second cubic attenuator was inferred, not independently established |
| Does `module-echo-cancel` actually load, or does it only exist on disk? | `reported`: `pactl load-module module-echo-cancel source_name=… sink_name=… aec_method=webrtc source_dont_move=true sink_dont_move=true` returned a module id with `libwebrtc-audio-processing-1.so.3` installed; a 2 s recording from the resulting source registered −57.9 dBFS rms. This does not establish effective cancellation |

Echo cancellation is a candidate for reducing reply-triggered wake words, not a
demonstrated solution. The tone results do not establish speech level or a
comparison with a person speaking across the room. Effective cancellation and
wake-word behavior are `unknown`; a future test needs separate authorization.
The historical observation also warns that omitting `source_dont_move` and
`sink_dont_move` may change default routing; this is not a verified procedure.

### Consequence for the "all outputs" profile

The reported results motivate investigation of member and virtual-sink volume,
but do not establish a correct default, safe level, or harmless behavior when a
member is unplugged. The interface above is a design sketch only.

The page reports using a tone at 36 % of the member sink's volume and the
microphone as detector. The separate [audio-levels result](../testing/results/2026-11-15-lab-pi5-audio-levels.md)
records a tone sweep, not the combine-sink check; it cannot establish speech
loudness or safety.

The reported HDMI observation suggests that an "all outputs" design must not
equate sink existence with an attached display. How to detect presence and handle
unavailable selected outputs remains `unknown`.

## Why this is not being built now

It would touch the audio server, the service that runs the voice assistant, and
the boot path at the same time. Earlier power sag is historical; James reports
improvement with a replacement supply, not a new measurement. It belongs
with `A02` (hardware profiles, gains and routing) and `M04` (coexistence policy),
both of which are blocked on a verified baseline — which is now closer, because
the speaker line-path finding removes a wrong assumption from that baseline.
