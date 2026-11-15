# Unattended research backlog

These are bounded desk studies for the scheduled runner, not roadmap completion
or permission to operate devices. Each scope below is the **entire task prompt**;
the runner copies it verbatim and appends its normal guardrails when executing.
Results are unreviewed handoffs, not approved decisions. Sources and open questions
come from the linked project notes; blocked physical work stays not-ready.

## Format

Exactly one fenced block labelled `debra-research-backlog`, closed by a line
containing exactly three backticks. One entry per line, in priority order:

`id | ready-or-not-ready | title | scope-and-complete-prompt`

Use the literal separator ` | `, no other `|` characters, no empty fields or
leading/trailing field whitespace. IDs use 1–128 ASCII letters, digits, `_` or
`-` and start with a letter or digit. Readiness is exactly `ready` or
`not-ready`; title and scope are single-line text, and scope is at least 40
characters. Blank lines are ignored. Malformed lines are reported and skipped;
all occurrences of a duplicate valid ID are skipped. A missing, duplicated or
unclosed block rejects the whole backlog. IDs already present in the queue in
**any** state are never reused; give a genuinely new follow-up a new ID. Editing
an already-queued entry does not alter that queued task. Add explicit research
scope and constraints to each new prompt; the program does not write prompts.

## Candidates

```debra-research-backlog
R07-ROCK3C-DTS | ready | ROCK 3C HAT schematic and device-tree evidence | Read docs/notes/2026-11-15-alternative-board-screen-revision.md and investigate public ROCK 3C V1.4 schematic and vendor kernel source for I2S3, I2C3 pinmux and codec bindings relevant to the ReSpeaker 2-Mics HAT. Cite exact revisions and links, distinguish documented wiring from driver availability, and identify missing evidence and the separately authorized physical test. No board access, installation or repository edits.
R07-ORANGE3B-PINS | ready | Orange Pi 3B audio header pin evidence | Read docs/notes/2026-11-15-alternative-board-screen-revision.md and inspect the vendor Orange Pi 3B pin-table images or schematic for header positions 3, 5, 12, 35, 38 and 40. Cite the exact board revision and source, transcribe only legible functions, and identify remaining electrical, driver and physical-fit unknowns. No purchase, device access, installation or repository edits.
N01-NM-CHECKPOINT | ready | NetworkManager checkpoint API for Wi-Fi rollback | Read docs/notes/2026-11-15-wifi-onboarding-options-revision.md and check NetworkManager's public versioned D-Bus checkpoint documentation and source for creating, confirming and rolling back a connection change without an interactive terminal. Report version scope, timeout and failure semantics, unresolved risks, and a proposed offline fixture test. Do not change networking, contact devices, install anything or edit repository files.
N01-AVAHI-CONFLICT | ready | Avahi hostname conflict behavior | Read docs/notes/2026-11-15-wifi-onboarding-options-revision.md and investigate Avahi's public documentation and source for host-name collision detection, renaming, persistence and notification to a headless application. Cite exact source revisions and distinguish RFC advice from Avahi's implementation. List unknowns and a future separately authorized device test; do not contact devices or edit repository files.
Z01-TFLITE-SOURCE | ready | ARMv6 TensorFlow Lite build requirements | Read docs/research/2026-11-15-armv6-wheels.md and investigate public source and build documentation for the TensorFlow Lite runtime needed by the identified wake-word engines. Identify versioned source, toolchain and CPU instruction assumptions and a plausible ARMv6 build investigation, with explicit unknowns. Do not build, install, access devices or claim that a wheel tag proves execution.
B01-TRIXIE-OVERLAY | ready | Raspberry Pi OS Trixie overlay options | Read docs/notes/2026-11-15-storage-durability.md and investigate public Raspberry Pi OS Trixie package and raspi-config sources for overlayroot availability and the overlay filesystem option. Cite exact versions and sources; explain persistence and recovery limitations without recommending device changes. No installation, device contact or repository edits.
OPT01-HOUSED-SPEAKERS | ready | Alternative housed speaker modules a case could carry | Survey publicly sold small housed speaker modules, roughly 30 to 110 mm on the long edge, that a Pi Zero satellite case could carry; for each record module type, published dimensions, connector, required supply voltage, whether it needs a separate amplifier, and where its acoustic openings are. Compare at least six against the envelopes in models/components/dweii-speakers/ and say which are plausible alternatives to the three owned DWEII modules and why. Cite sources with access dates, treat seller dimensions as claims rather than measurements, contact no supplier, and write an unreviewed note under docs/notes/ dated with the run date.
OPT02-MIC-INTERFACES | ready | Microphone interface options for a Pi Zero satellite | Compare the microphone paths available to a Pi Zero satellite: an I2S HAT with an onboard ADC, a USB microphone, and an I2S microphone module wired to the board. For each, cite what is documented about driver support on 32-bit Raspberry Pi OS, whether the vendor kernel patches are needed, how it appears to ALSA and PipeWire, the power draw implications, and whether the speaker amplifier is separate. Say plainly which claims are upstream documentation, which are vendor or forum reports, and which are unknown; write an unreviewed note under docs/notes/ dated with the run date.
OPT03-CASE-FASTENERS | ready | Fastener and insert options for a printed Debra case | Survey the practical options for fastening 3D printed case parts: self-tapping screws into printed bosses, heat-set threaded inserts, snap fits and screwless clips. For each give the recommended boss wall thickness and hole diameter for common insert and screw sizes, the material assumptions for PLA and PETG, the tooling needed, and the failure modes. Cite manufacturer dimension tables with access dates and avoid repeating generic advice without a source. Finish with a recommendation for a case that must be opened often for development, and write an unreviewed note under docs/notes/ dated with the run date.
V17-SPEAKER-PHOTO | not-ready | Identify the original four-screw speaker mount | Obtain a human-provided photograph of the assembled original with the cover off or the missing part file, then identify what the four screws enter as described in docs/work-queue.md. This requires a person and must not be dispatched as an unattended desk study.
A03-DEVICE-CONTROL | not-ready | Verify music interruption on the lab device | Perform a separately authorized named-device test of pause and independent duck behavior, with recovery and agreed audio levels, following docs/roadmap.md A03 and docs/notes/2026-11-15-music-transport-and-control-map.md. This requires device access and must not be dispatched unattended.
```
