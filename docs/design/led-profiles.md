# LED profiles, events, brightness and mute

**Specification for review, 2026-11-15. Not implemented, not tested, not approved.**
No device was contacted and no LED was written while writing this page. It exists
because [roadmap A04](../roadmap.md) and [WEB06](../design/web-control.md) both
depend on it and both are blocked on hardware work. Treat every pattern below as
a proposal to be argued with, not as behaviour.

This page does not create a second task ledger. A04 owns the work; this page is
the detail A04 and WEB06 can implement and test against.

Evidence labels follow [docs/evidence.md](../evidence.md): `tested`,
`upstream-documented`, `reported`, `hypothesis`, `unknown`.

---

## 0. The short version

- Three profiles, chosen for three different jobs: **Standard** (show what it is
  doing), **Night** (be dark unless something needs you), **Mic truth** (show
  only whether the microphone is capturing).
- Brightness scales visibility and never carries meaning. Meaning lives in
  position, motion and colour, in that order, because colour fails when dim.
- The microphone is capturing in every ordinary state, including idle. No
  profile may display a "not listening" signal unless capture is genuinely
  stopped.
- The ReSpeaker 2-Mics HAT has **no hardware mute**. Its button is software.
  Assistant mute is not microphone mute, and the LEDs must not pretend otherwise.

---

## 1. The three profiles

A profile is a *purpose*, not a colour scheme. Two profiles that differ only in
hue are the same profile. The test for whether these are genuinely different:
they disagree about what is worth showing, so the same event produces
"informative", "invisible" and "irrelevant" in the three columns.

### 1.1 Standard (default)

- **For:** knowing what the device is doing without opening a browser.
- **Suits:** a living room, kitchen or hallway. Anyone who wants a visible
  answer to "did it hear me, is it working, is something wrong".
- **Shows:** the full vocabulary in section 2, with position and motion
  separating states, plus one user-chosen accent colour.
- **Deliberately does not show:** whether capture is live while the assistant is
  muted (it shows assistant-mute only, and says so in the UI); audio level; a
  timer countdown with any resolution (three LEDs cannot show minutes); which of
  several possible errors occurred; network detail beyond up or down.

### 1.2 Night

- **For:** a device in the room where someone sleeps.
- **Suits:** a bedroom or nursery. Anyone for whom a glowing object at 03:00 is a
  defect, not a feature.
- **Shows:** almost nothing. Capture-off is the only steady light it is allowed
  (section 4), and faults and connection loss are a single dim burst at the
  moment they happen, then dark.
- **Deliberately does not show:** idle, wake word, recording, thinking, speaking,
  music, assistant mute after its transition, and any repeating reminder. It
  does not show wake-word detection because a flash every time someone talks in
  bed is the brightest thing in the room and the least useful.
- **The trade it accepts:** at night, idle and assistant-muted look identical
  (both dark). This is declared, not hidden. The web UI and Home Assistant
  remain authoritative, and the profile is not offered as suitable for someone
  who needs to see mute state from across a dark room.

### 1.3 Mic truth

- **For:** answering one question only, "is the microphone capturing right now".
- **Suits:** someone who does not trust a smart speaker's own status light and
  wants a lamp that means exactly one thing. Also useful for review and
  demonstration, because it is falsifiable.
- **Shows:** the outer two LEDs as a microphone lamp (dim white: capturing, dim
  red: not capturing), and the centre LED for the three things that change the
  answer's meaning: assistant muted, fault, wake word acknowledged.
- **Deliberately does not show:** thinking, speaking, music, connection state as
  its own signal (connection loss recolours the mic lamp, it does not add a new
  display), or any decorative idle colour.
- **The trade it accepts:** the outer pair is lit whenever the device is
  capturing, which is nearly always. This profile is for people who prefer a
  visible reminder to a dark room. It is not a hardware mute light and must never
  be described as one (section 5).

### 1.4 Relationship to the existing placeholder wording

[WEB06](../design/web-control.md) currently says "off/dim/default/custom".
Those are a brightness axis (`off`, `dim`), a default, and an escape hatch, not
three purposes. This specification keeps the useful parts and maps them:

| WEB06 wording | Here |
| --- | --- |
| `default` | Standard |
| `dim` | Night |
| `off` | global brightness at 0 (section 4), available in every profile, not a profile |
| `custom` | a user-editable copy of any built-in profile, not a fourth built-in |

Review point: if WEB06's four words were meant literally as four selectable
items, this page is proposing a change to them, and that change belongs in
WEB06, not here.

---

## 2. Event vocabulary

The eleven states James named, plus one that already exists in the voice runtime
and cannot be ignored (timer). For each: is it a brief event or a continuing
state, and is the microphone capturing during it.

| # | Name | Kind | What is actually true | Capture live |
| --- | --- | --- | --- | --- |
| E1 | Idle / listening for wake word | state, continuous | the local wake-word model is running on a live capture stream | **yes** |
| E2 | Wake word detected | event, about 0.3 to 0.6 s | transition only | yes |
| E3 | Recording (utterance) | state, seconds | audio is leaving the device for speech-to-text | yes |
| E4 | Thinking | state, variable | the reply is being produced elsewhere | `unknown` |
| E5 | Speaking | state, seconds | reply or announcement is playing | `unknown` |
| E6 | Music playing | state, minutes to hours | media playback, unrelated to voice | `unknown` |
| E7 | Error | event, brief | a pipeline step failed | unchanged by the error |
| E8 | No network | state, continuous | no usable link | yes, locally |
| E9 | No Home Assistant | state, continuous | link is up, the assistant backend is not reachable | yes, locally |
| E10 | Muted | state, continuous | see section 5: the assistant will not respond | **yes, unless capture mute is separately implemented** |
| E11 | Timer ringing | state, continuous until stopped | an alarm is sounding | `unknown` |

Decisions this table makes, which a reviewer should confirm or reject:

1. **Idle and "listening for wake word" are the same condition** on this device,
   because the wake model runs continuously. They are merged into E1. Inventing
   two LED states for one condition would be a lie about the hardware. A separate
   "listening" state in the sense of "capturing an utterance" is E3, recording.
2. **Idle is not off.** E1 means the microphone is live and the device is
   waiting. Any display that makes E1 look like "off" is the failure described in
   section 8.
3. **E4, E5, E6 and E11 have unknown capture state.** The voice runtime documents
   that muted audio is not sent, but not whether the capture stream is closed
   between utterances. Until that is measured (section 6.3), no profile may
   assert capture-off in those states, and the Mic truth profile's mic lamp must
   follow the measured truth rather than a guess.
4. **Timer is included** because the runtime already emits timer events and
   WEB06 already lists it. Leaving it undefined would be exactly the silent drop
   section 8 forbids. A profile that cannot show it must say so in the table.

### 2.1 Event versus state, and why it matters

Events are short and may be missed by a glance. States persist and must be
readable at any moment. The rules that follow:

- An event must not be the only indication of a lasting problem. E7 (error) is a
  burst, but if the device stays broken the lasting condition must appear as a
  state (E8, E9) or in the UI.
- A state must not be rendered as a one-shot event. Muted is not a flash; it is
  a condition that persists until changed.
- An event that occurs while a state is displayed must not cancel the state. The
  error burst returns to what was showing.

---

## 3. The mapping table

Three LEDs, indexed 0, 1, 2 left to right as the user sees the board. All three
sit in one 6.35 mm row near the middle of the HAT (section 6), so they read as a
short bar, not a ring.

Pattern vocabulary, deliberately small:

| Term | Meaning |
| --- | --- |
| solid | steady, no change |
| breathe | brightness follows a sine, one cycle per 2 to 5 s |
| blink | on/off at a stated rate, square |
| chase | one LED lit at a time, moving along the row and back |
| burst | a fixed number of blinks, then return to the previous display |

Nothing else is available. There is no gradient, no text, no countdown, no
direction indicator, and no way to show two independent things on one LED.

### 3.1 Standard

| Event | LEDs | Pattern | Colour | State factor |
| --- | --- | --- | --- | --- |
| E1 Idle | 0,1,2 | solid | user accent (default soft blue) | 30% |
| E2 Wake word | 0,1,2 | burst, 2 blinks at 4 Hz | user accent | 100% |
| E3 Recording | 0,1,2 | chase, 0-1-2-1 at 1.5 Hz | user accent | 100% |
| E4 Thinking | 0,1,2 | breathe, 0.3 Hz | amber | 60% |
| E5 Speaking | 0,1,2 | breathe, 0.25 Hz | green | 60% |
| E6 Music | 1 only | breathe, 0.2 Hz | white | 25% |
| E7 Error | 0,1,2 | burst, 3 blinks at 4 Hz | red | 100% |
| E8 No network | 0,1,2 | double blink, 1.8 s cycle | dim red | 30% |
| E9 No Home Assistant | 0,1,2 | single blink, 3 s cycle | dim amber | 30% |
| E10 Assistant muted | 1 only | solid | purple | 40% |
| E11 Timer ringing | 0,1,2 | burst repeating at 1 Hz | blue | 100% |
| Capture disabled | 0,2 | solid | red | 30% |

### 3.2 Night

| Event | LEDs | Pattern | Colour | State factor |
| --- | --- | --- | --- | --- |
| E1 Idle | none | off | - | 0 |
| E2 Wake word | none | off | - | 0 |
| E3 Recording | none | off | - | 0 |
| E4 Thinking | none | off | - | 0 |
| E5 Speaking | none | off | - | 0 |
| E6 Music | none | off | - | 0 |
| E7 Error | 0,1,2 | burst, 3 blinks at 2 Hz, once | red | 6% |
| E8 No network | 0,1,2 | burst, 2 blinks at 2 Hz, once | amber | 6% |
| E9 No Home Assistant | 0,1,2 | burst, 1 blink, once | amber | 6% |
| E10 Assistant muted | 1 only | burst, 1 blink at the transition only | purple | 4% |
| E11 Timer ringing | 0,1,2 | burst, 3 blinks at 1 Hz, once | blue | 6% |
| Capture disabled | 0,2 | solid | red | 2% |

Notes a reviewer must accept or reject:

- Capture disabled is the **only** steady light Night permits, and it is capped
  at 2% (section 4). The reason is usability, not decoration: without it, a
  person who muted capture yesterday talks to a dark device that cannot hear
  them. A 2% red pair is not "bright at night" in any ordinary sense, but this is
  an explicit exception to the rule and it is written here rather than left to
  the implementer.
- Every burst is emitted once per transition. Nothing repeats. A device that
  blinks every 60 s all night has failed the requirement.

### 3.3 Mic truth

The outer pair is the microphone lamp. Its colour is the claim, and it is the
same signature in all three profiles, so it is learnable once.

| Event | LEDs 0 and 2 (mic lamp) | LED 1 | State factor |
| --- | --- | --- | --- |
| E1 Idle | solid white | off | 10% |
| E2 Wake word | solid white, unchanged | burst, 2 blinks at 4 Hz, white | 25% |
| E3 Recording | solid white | breathe, 0.3 Hz, white | 20% |
| E4 Thinking | solid white | off, not shown | 10% |
| E5 Speaking | solid white | off, not shown | 10% |
| E6 Music | solid white | off, not shown | 10% |
| E7 Error | solid white, unchanged | burst, 3 blinks at 4 Hz, red | 50% |
| E8 No network | solid amber | off | 10% |
| E9 No Home Assistant | solid amber | burst, 1 blink every 5 s, amber | 10% |
| E10 Assistant muted | solid white (capture is still live) | solid purple | 20% |
| E11 Timer ringing | solid white | burst repeating at 1 Hz, blue | 50% |
| Capture disabled | solid red | off | 20% |

### 3.4 Precedence when several are true at once

Without this, two implementations of the same table disagree, and one of them
will hide a fault behind a mute. The order is fixed and identical in all
profiles.

| Channel | Order, highest first |
| --- | --- |
| LEDs 0 and 2 | capture disabled, then no network or no Home Assistant, then activity, then idle |
| LED 1 | error burst, then timer ringing, then assistant muted, then wake word or recording, then thinking or speaking, then music, then off |

The capture-off signature therefore always wins the outer pair, and a fault
always wins the centre. This is what makes "the mic is dead" unmissable even
while the device is also complaining about the network.

### 3.5 What three LEDs cannot express, and the profile says so

| Wanted | Why not | Resolution |
| --- | --- | --- |
| Which error occurred | one red burst is one red burst | web UI names it; the LED only says "fault" |
| Timer remaining time | no resolution below a minute, and no direction | sound carries it; the LED says "ringing" |
| Audio level or VU | it would make brightness a state (section 4) | never shown |
| Two simultaneous activities | one centre LED | precedence table, plus the UI |
| Colour-coded state at 2% brightness | hue is unreliable when dim and for colour-blind users | position and motion carry the meaning first |

### 3.6 Other LED counts

The profiles must not assume three. A one-LED device can show the centre column
only, which loses the capture lamp; the honest result is that the Mic truth
profile is **unsupported** on one LED, not approximated. A 12 or 24 LED ring can
render the same table with position mapped onto arc segments. The rule: degrade
by declaring unsupported cells in the UI, never by inventing a pattern.

---

## 4. Brightness

Two multipliers, and no third meaning:

| Control | Range | Default | What it does |
| --- | --- | --- | --- |
| Global brightness B | 0 to 100 | 40 | scales every rendered frame in every state |
| State factor F | 0 to 100 per row above | per table | how prominent that state is relative to others |

Effective level is B x F, rounded down, and anything under about 1% is rendered
as off rather than as a ghost glow.

**Brightness never means anything.** A dim error is not a lesser error, and a
bright idle is not a more idle device. If a user cannot tell a dim red from a dim
amber, that is a colour problem to fix in the table, not a brightness problem to
fix by turning it up. This is also why audio-level indication is excluded
everywhere: it turns brightness into a state and destroys the separation.

### 4.1 Night mode is not the Night profile

They are different mechanisms and both are needed:

| | Night profile | Night mode |
| --- | --- | --- |
| Question it answers | what is worth showing at all | when nothing should be bright |
| Scope | one device, chosen once | a schedule or manual toggle, any profile |
| Effect | suppresses cosmetic states by design | caps B at a ceiling (default 6%) and suppresses idle glow, music, thinking and speaking |

They combine: Night profile plus night mode is the darkest configuration. Any
profile plus night mode is a bright device that goes quiet at the right hour.
The default schedule should be off until the user sets it, because a device that
silently dims at a time the user did not choose looks broken.

### 4.2 At zero

B = 0 means every LED is off in every state, including capture-off and errors.
Consequences that must be made explicit rather than discovered:

- Events are still processed, still logged, and still visible in the web UI and
  Home Assistant. Zero brightness suppresses light, not information.
- The UI must state, at the point where the user sets 0, that the LED can no
  longer indicate mute or capture state. A device that cannot show mute must not
  be documented as if it can.
- Zero is not the factory default, and a failed configuration load must not fall
  back to 0. It falls back to the last known working value.

---

## 5. Mute

Three different things are called mute. Only one of them stops the microphone.

| Kind | What it does | Is capture stopped | LED may claim capture-off |
| --- | --- | --- | --- |
| Assistant mute (the LVA Mute switch, and Debra's default mute) | wake word and stop word disabled, a running reply is stopped, no audio sent to Home Assistant | **no evidence that it is** | **no** |
| Capture mute (codec or ALSA capture path disabled) | the device delivers no samples at all | yes, in software | yes, if verified per section 6.3 |
| Hardware mute | a switch removes microphone power or gates the signal | yes, physically | yes |

### 5.1 What the evidence actually says

The voice runtime's own documentation states that when muted, the wake word and
stop word are disabled and "no microphone audio is sent to Home Assistant". It
does **not** state that the capture stream is closed. So the honest label for
assistant mute is: the assistant will not respond, and audio does not leave the
device; whether the microphone is still capturing locally is `unknown` and
untested.

This matters because the same documentation tells peripheral authors to show
muted as "red at mic positions". A red light at the mic positions, while the
microphone is probably still capturing, is precisely the claim this
specification forbids. Debra's table therefore uses **purple on the centre LED**
for assistant mute and reserves **red on the outer pair** for a verified capture
stop. Reviewers should treat that upstream guidance as a trap, not a pattern to
copy.

### 5.2 Which the device offers

- Assistant mute is always available, on every HAT, because it is software.
- Capture mute is available only if the codec exposes a capture control that
  demonstrably stops samples. Not established (section 6.3). If it is not
  available, the capture-off display must never appear and the UI must not offer
  a control that implies it.
- Hardware mute does not exist on the ReSpeaker 2-Mics HAT. The onboard button
  is a GPIO input read by software, and software can be wrong, wedged or
  bypassed. A device with a real hardware mute (the Satellite1 HAT, for example)
  is a different and stronger privacy claim, and the UI should say which one the
  detected hardware has.

**A HAT without a hardware mute is still a valid profile.** The requirement is
not that every device can kill its microphone. It is that no device claims a
capability it lacks. A board with no LEDs, no button and no mute is still a
supported configuration: the profiles apply, every LED cell is reported
unavailable, and assistant mute remains a web and Home Assistant control.

---

## 6. What the hardware can and cannot do

### 6.1 Established

| Fact | Value | Label | Source |
| --- | --- | --- | --- |
| LED count and type, ReSpeaker 2-Mics Pi HAT | 3 x APA102 RGB, each with its own driver chip, holding colour until rewritten | upstream-documented | Seeed wiki, product page, and the v2 getting-started page |
| Interface | SPI0: data on GPIO10 (MOSI), clock on GPIO11 (SCLK), device `/dev/spidev0.0` | upstream-documented | Seeed v2 page (SPI must be enabled), LVA ReSpeaker example pin table |
| Physical layout | three 2.2 x 1.9 x 0.7 mm packages at x = 29.34, 32.51, 35.69 mm, y = 18.16 mm on a 65 x 30 mm board, so 3.17 mm pitch and a 6.35 mm total span, all near the board centre | upstream-documented | Seeed V1.0 Eagle `.brd`, parsed in [the component envelope](../../models/components/respeaker-2mic-hat/README.md) |
| Button | one tactile button on GPIO17, active low, read by software | upstream-documented | Seeed v2 page, LVA example |
| On Pi 5 | the vendor button demo needs `gpiozero` because `RPi.GPIO` does not work | upstream-documented | Seeed v2 page |
| Diffuser | none on the HAT. Visibility is decided by the enclosure | upstream-documented | board file; [enclosure arrangements](enclosure-arrangements.md) |
| LED control on the lab device | **not exercised.** The audio test record lists APA102 control as untested | tested (as a non-result) | [Pi 5 audio record](../testing/results/2026-11-15-pi5-respeaker-v2-audio.md) |
| A reference implementation exists | an LVA peripheral example drives exactly these 3 LEDs and this button, with an animation table close to section 3.1 | upstream-documented | LVA `examples/ReSpeaker 2mic HAT` |

Two corrections to carry forward:

- The LVA example says LED 0 sits above MIC_L and LED 2 above MIC_R. On the real
  board all three LEDs are within 6.35 mm of each other at the centre, while the
  microphones are 59 mm apart at the ends. The mic-position reading is a
  **symbolic convention**, not physical geometry, and the spec uses it that way.
  Nobody should promise a user that the outer LEDs are over the microphones.
- That example also describes a WM8960 codec, which is the v1 HAT. The LED and
  button wiring is unchanged in v2, but the document is not a v2 audio reference.

### 6.2 Other candidate boards

| Board | LED hardware | Mute | Label |
| --- | --- | --- | --- |
| Waveshare WM8960 Audio HAT | no LEDs | none | reported, per [preliminary findings](../research/2026-11-14-preliminary-findings.md) |
| Satellite1.1 HAT | 24 x WS2812 | four buttons, one of them a hardware mute | reported, per [comparison sources](../comparisons/sources.md) |
| M5Stack ATOM Voice | one SK6812 | none | reported, per [comparison sources](../comparisons/sources.md) |

So the LED count in the field is 0, 1, 3, 12 and 24. Three is one case, not the
model.

### 6.3 Not established, and what would settle each

| Unknown | Why it matters | What settles it |
| --- | --- | --- |
| Whether the parts are genuine APA102 or a pin-compatible clone (SK9822 and similar) | clones differ in low-brightness behaviour and colour accuracy, which is exactly the Night profile's working range | part marking under magnification, plus a measured ramp of global brightness 1 to 31 at fixed channel values |
| Whether the LEDs are comfortable in a dark bedroom at the lowest usable setting, with no diffuser | Night's 2% and 6% figures are invented until measured | a dark-room test: photograph at fixed exposure, and a lux reading at 1 m, for each level used in section 3.2 |
| Whether hue survives at those levels | red, amber and purple may all read as "dim warm dot", which breaks section 3's colour column | the same dark-room test, with an observer naming colours, and a colour-blind check |
| Whether SPI0 is free on the lab Pi 5 with the v2 overlay | if CE0 or the bus is taken, the reference implementation does not run as written | enable SPI, run the LVA example, and confirm the codec still captures and plays |
| Whether the TLV320AIC3104 driver exposes a capture control that actually stops samples | it decides whether capture mute exists at all, and therefore whether the capture-off display may ever be shown | enumerate `amixer -c seeed2micvoicec` controls, toggle each candidate, and confirm with a loopback that no samples arrive |
| Whether the voice runtime keeps the capture stream open while muted | it decides whether E10 is cosmetic or real, and it is the privacy claim at the centre of this page | run the runtime, mute it, and inspect the open capture device and the audio graph from another shell |
| Whether the microphone is capturing during thinking, speaking, music and timer | the `unknown` cells in section 2 | the same capture-device inspection across a full interaction |
| Which enclosure the LEDs end up behind | the upright arrangement puts them under the driver, so they may be invisible without a light pipe | an enclosure decision plus a visibility test on the assembled unit |

The power fault is relevant here. The lab Pi 5 sags and resets under load with
the current supply. An LED animation is extra current, and Standard's 100%
factors coincide with speaking and with a ringing timer, which are also the
loudest moments. Sustained high brightness during playback is not free on this
device, and the implementation should be able to cap LED current while audio is
playing rather than discover the interaction during a demo.

---

## 7. Acceptance criteria for a future implementation

Each statement is checkable without reading the implementation.

1. **Every vocabulary row is handled.** A test enumerates E1 to E11 plus capture
   disabled and fails if any has no defined rendering in the selected profile.
2. **The table matches the device.** For each row, a recorded video or an LED
   state trace shows the documented pattern, colour and relative level, on real
   hardware, for each of the three profiles.
3. **Nothing is silently dropped.** With logging on, every state change and every
   event appears in the device log with the rendering chosen, including rows the
   profile suppresses.
4. **Zero brightness is truly dark.** At B = 0, every row including capture-off
   and error produces no light, verified in a dark room.
5. **Night is dark.** In the Night profile, no state exceeds the 6% ceiling
   except capture-off at 2%, no light is steady except capture-off, and nothing
   repeats. Verified by the same dark-room recording over a full interaction.
6. **Night mode caps any profile.** With night mode active on Standard, no state
   exceeds the night ceiling and idle, music, thinking and speaking are
   suppressed.
7. **Brightness is not a state.** Changing B does not change which state is
   displayed, and no state is distinguishable from another only by brightness.
8. **The capture claim is never false.** With the assistant muted and the
   capture device verified open, no profile displays the capture-off signature.
   This is the privacy criterion and it is the one that must not be waived.
9. **Capture-off requires a verified stop.** If capture mute is implemented, the
   capture-off signature appears only when a concurrent recording attempt yields
   no samples. If capture mute is not implemented, the signature is unreachable
   in every profile and the UI does not offer the control.
10. **Unsupported is stated.** On a board with no LEDs, the UI reports every LED
    cell as unavailable. On a one-LED board, the Mic truth profile reports
    unsupported rather than approximating it.
11. **Restart is safe.** Power loss or restart never leaves a stale bright
    pattern: the device comes up in the configured profile at the configured
    brightness, or dark, and never at full white.
12. **Apply, preview and rollback.** A mapping change can be previewed without
    lighting the device unexpectedly, applied atomically, and rolled back to the
    last working configuration, with the old mapping restored and verified.
13. **The button does not lie.** If the button toggles assistant mute, its
    confirmation sound and its LED agree, and a held or repeated press cannot
    leave the displayed mute state out of step with the real one.

---

## 8. What must never happen

1. **An LED that claims "not listening" while the microphone is live.** No
   steady red mic lamp, no "off" idle that means "mic dead", no reuse of the
   capture-off signature for assistant mute. This is the failure the whole
   specification is arranged around.
2. **A profile that leaves the device bright at night.** No steady light in
   Night except capture-off at 2%, no repeating reminder, and no state that
   ignores the night ceiling because it is "important". Importance is expressed
   by contrast within the ceiling, not by exceeding it.
3. **An event that is silently dropped.** A profile may declare a row as not
   shown. It may not fail to define it, and it may not lose an event at runtime
   because a display update was already in flight.
4. **Brightness used as a state.** No audio level meter, no "dimmer means less
   important", no state that can only be told apart by how bright it is.
5. **A mute control that overstates itself.** No UI wording, no documentation
   and no LED pattern may imply the microphone is dead when only the assistant
   is muted, and no device may be described as having a hardware mute it does
   not have.
6. **A pattern invented for hardware that cannot show it.** No approximation of
   the mic lamp on one LED, no pretence that a 24 LED ring renders the same
   three-LED table exactly.
7. **A full-white or full-brightness boot.** Including after a failed
   configuration load, and including the moment before the profile is applied.
8. **LED work on the audio path.** A wedged or slow LED update must not stall
   capture or playback, and an LED failure must never take the assistant down.

---

## 9. Open questions for the reviewer

1. Is merging idle and "listening for wake word" correct, or does James expect a
   visible difference between "waiting" and "capturing an utterance"?
2. Is a steady mic lamp in the Mic truth profile acceptable given that it is lit
   almost permanently, or should that profile be pulse-on-change only?
3. Should Night's capture-off exception exist at all, or is absolute darkness
   more important than warning a user who muted capture the night before?
4. Is purple for assistant mute the right call, given that it is a colour with no
   meaning anywhere else in the system?
5. Does WEB06 keep its `off/dim/default/custom` wording, or adopt the three
   purposes here?
6. Which of the unknowns in section 6.3 must be settled before A04 is unblocked,
   and which can be settled during it?

## 10. Sources

- Seeed Studio, ReSpeaker 2-Mics Pi HAT wiki: 3 APA102 RGB LEDs on SPI, button on
  GPIO17, Grove ports. https://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT/
  (checked 2026-11-15)
- Seeed Studio, Getting Started with Raspberry Pi, v2 page: SPI must be enabled,
  each APA102 has a driver chip, GPIO17 button, `gpiozero` needed on Pi 5.
  https://wiki.seeedstudio.com/respeaker_2_mics_pi_hat_raspberry_v2/
  (checked 2026-11-15)
- Seeed Studio, ReSpeaker 2-Mics Pi HAT V1.0 Eagle board file, for LED positions.
  Parsed in [models/components/respeaker-2mic-hat](../../models/components/respeaker-2mic-hat/README.md).
- OHF-Voice Linux Voice Assistant, peripheral WebSocket API: events, the `muted`
  event, and the guidance to show mute as red at the mic positions.
  https://github.com/OHF-Voice/linux-voice-assistant/blob/main/docs/peripheral_api.md
- OHF-Voice Linux Voice Assistant, behaviour guide: what the Mute switch does and
  does not do. https://github.com/OHF-Voice/linux-voice-assistant/blob/main/docs/behavior.md
- OHF-Voice Linux Voice Assistant, ReSpeaker 2mic HAT example: pin table, LED
  positions and animation table.
  https://github.com/OHF-Voice/linux-voice-assistant/blob/main/examples/ReSpeaker%202mic%20HAT/DOCS.md
- Debra, [Pi 5 ReSpeaker v2 audio record](../testing/results/2026-11-15-pi5-respeaker-v2-audio.md):
  the board works for audio; LED control is listed as untested.
- Debra, [alternative board screen](../notes/2026-11-15-alternative-board-screen.md):
  SPI, GPIO17 and I2C requirements for this HAT.
- Debra, [comparison sources](../comparisons/sources.md): Satellite1.1 (24
  WS2812, hardware mute) and M5Stack ATOM Voice (one SK6812).
- Debra, [enclosure arrangements](enclosure-arrangements.md): the upright
  arrangement puts the LEDs under the driver.

This page is not yet linked from [docs/README.md](../README.md). Adding it there
is a separate edit outside this task's scope.
