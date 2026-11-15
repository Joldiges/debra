# Audio outputs: choosing, and playing to all of them

James asked for this on 2026-11-15: *"the user should be able to easily select
which outputs it runs on — or maybe even on 'all' at once such that any one
plugged in will be had."*

**Requirement and design options, not implemented behaviour.** What is actually
proven on the lab device is marked `T`; everything else is proposed or unknown.

## "Output" means three different things

Most confusion about audio outputs comes from collapsing these. They are
independent, and each needs its own setting.

| Layer | What it is | On the lab Pi today |
| --- | --- | --- |
| **Codec taps** | One sound card, several physical output pins on the codec: line out, headphone out, composite out. All can be live at once with independent gains | `T` — the HAT's speaker is on **line out**; headphone and composite are silent |
| **Sinks** | PipeWire nodes, one per physical device: the HAT card, HDMI 0, HDMI 1, any USB DAC | `T` — only the HAT sink exists, because both HDMI ports are disconnected |
| **Network players** | Sendspin and Snapcast: the music goes out over the network to a player, which is a different transport entirely | `T` — Sendspin 9.1.0 is running and pointed at the same sink |

A user who says "play on the speaker or the TV" is usually talking about layer 2.
A user who says "and my headphones too" is talking about layer 1. A user asking
"why does music go to the other room" is talking about layer 3.

## The finding that changes the design

The speaker on the ReSpeaker 2-Mics HAT is fed from the codec's **line output**
through the board's TPA2005D1 amplifier; the 3.5 mm jack is on the **headphone**
output. Measured on the bare card with PipeWire stopped, a 1 kHz tone played to
each path in turn and recorded by the HAT's own microphone:

| Path | Microphone at 1 kHz |
| --- | --- |
| `HP` (headphone, the jack) | nothing, ≈ −100 dBFS — no headphones were plugged in |
| `HPCOM` (composite) | nothing, ≈ −90 dBFS |
| `Line` (the speaker) | **−21 dBFS** |

Two consequences:

- **"Correct mixer, no sound" is a real state.** Every service was active, the
  sink existed at 65 %, and the device was silent because `Line DAC` was at zero
  gain. The mixer script sets it; the *stored* `alsactl` state had drifted, and a
  state saved before the script ran survives every reboot. Check the line gain
  before anything else, and note that `HP DAC` is not the speaker's control.
- **The codec taps are already an "all" switch.** Enabling `Line` and `HP` at
  sane gains costs nothing and makes a plugged-in headphone work without
  software noticing. That is the cheapest half of what James asked for, and it
  is why the headphone tap is left at 0 dB even though nothing is in the jack.

## Layer 2: one sink, or all of them

| Option | How | Good | Bad |
| --- | --- | --- | --- |
| **One selected sink** | Set the PipeWire default sink to the user's choice | Simplest, no drift, works with any player | Nothing else plays; the user has to know the name |
| **Combine sink** | A virtual sink that fans out to several real sinks | "All at once" for announcements; one setting | Members are not clock-locked, so long playback drifts; each member has its own volume; HDMI only exists while a display is connected |
| **Default follows hotplug** | `module-switch-on-connect`: a newly connected device becomes the default | Plug in a TV, sound goes there | It *moves* the audio instead of adding it, so a plugged-in monitor silently steals the voice reply — exactly the failure the pinned `AUDIO_OUTPUT_DEVICE` was added to prevent |

The recommendation is a **combine sink as the default, with the single-sink
option kept**, because the two failure modes are not symmetric: a combine sink
that includes an unplugged output is harmless, while a hotplug default that
steals the voice reply is a bug report.

### Where the combine sink must not be used

Music. Sendspin and Snapcast do their own clock synchronisation across devices;
a combine sink would duplicate the stream into sinks with independent clocks and
break the thing those protocols exist for. So the rule is:

- **Voice, announcements, timers, chimes → the combine sink.** They are short,
  drift cannot accumulate, and being heard in every room is the point.
- **Music → one sink, chosen by the user.** Sendspin's own sync stays intact.

That split matches the existing product decision that duck/resume and pause/resume
are a user setting, and it is the same boundary `M04` describes as
"exclusive/shared audio ownership".

## What the user should actually touch

A small, boring interface, because this is a thing people set once:

```
debra-audio outputs                 # list what exists, what is connected, what is active
debra-audio outputs set speaker     # the HAT
debra-audio outputs set hdmi        # whichever HDMI port has a display
debra-audio outputs set all         # combine: everything currently present
debra-audio outputs follow on|off   # whether a newly plugged device becomes active
```

Underneath: a config file with the chosen profile, a systemd user unit that
applies it at boot and on device change, and `pactl`/`wpctl` calls that can be
run by hand when the UI is broken. No hidden state: the config says what should
be true, and `debra-audio outputs` reports what is true.

## What is not settled

- **Whether the 3.5 mm jack is on the line tap or the headphone tap.** The
  speaker is on line; the jack is untested. If the jack is also on line, then
  "speaker and headphones" cannot be separated by the codec and the only
  distinction is volume. **Next check:** plug headphones into the HAT, enable
  `HP`, play a tone, and see which tap makes sound. **Not tested on 2026-11-15
  because it needs audible output.**
- **Volume behaviour in a combine sink.** Whether the virtual sink's volume
  scales every member, and what happens when a member has a hardware volume
  control (the HAT's `PCM`), is untested.
- **Bluetooth.** Not considered at all. It is a sink like any other in
  principle, and it has its own latency and reconnect problems.
- **Whether the user wants music to follow the announcement profile.** Today
  they are separate by design; that is a decision to confirm, not a fact.

## What the lab Pi answered, 2026-11-15

Three of the open questions above are now measured rather than assumed. Nothing
audible was played, so none of this disturbs a sleeping house.

| Question | Answer |
| --- | --- |
| Is `module-combine-stream` available? | **Yes.** `libpipewire-module-combine-stream.so` is present on PipeWire 1.4.2 (`/usr/lib/aarch64-linux-gnu/pipewire-0.3/`), so the native PipeWire combine sink is usable and the PulseAudio-compat `module-combine-sink` is not needed |
| Is `module-echo-cancel` available? | **Yes.** `libpipewire-module-echo-cancel.so` is present, so the reply re-triggering the wake word can be attacked with a real echo-cancel sink instead of by lowering the volume |
| Do HDMI sinks appear with no display connected? | **Yes, and this contradicts what was assumed.** `alsa_output.platform-107c701400.hdmi.hdmi-stereo` exists in `SUSPENDED` state with nothing plugged into either port. Only HDMI **0** appears; HDMI **1** does not |

The HDMI answer changes the design: an "all outputs" combine sink would include a
dead HDMI member on a device with no screen. That is not harmful for a chime, but
it means "all" cannot be defined as "every sink that exists" — it has to be
"every sink the user has chosen, present or not", and the presence check has to
come from somewhere other than `pactl list sinks`.

## Why this is not being built now

It touches the audio server, the service that runs the voice assistant, and the
boot path at the same time, on a device whose power rail still sags. It belongs
with `A02` (hardware profiles, gains and routing) and `M04` (coexistence policy),
both of which are blocked on a verified baseline — which is now closer, because
the line-versus-headphone finding removes a wrong assumption from that baseline.
