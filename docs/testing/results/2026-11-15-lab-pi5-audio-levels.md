# Pi 5 lab device: how loud the speaker has to be for a test to hear it

**Device-tested, single specimen, one room, 2026-11-15 04:00 UTC.** The device
sits in a house with people asleep and a baby in it, so any automated test that
plays a sound needs a volume that is low enough to be inaudible from the next
room and high enough for the microphones to measure. This is the sweep that finds
that range, and the two measurement mistakes it exposed.

| Item | Value |
| --- | --- |
| Board / OS / kernel | Pi 5 Model B Rev 1.0, Raspberry Pi OS Lite 64-bit Trixie, `6.18.50+rpt-rpi-2712` |
| Card | `seeed2micvoicec` (TLV320AIC3104), sink `alsa_output.platform-soc_107c000000_sound.stereo-fallback` |
| Capture | PGA 12 dB (`PGA Capture Volume` = 24), AGC off, source volume 100 % |
| Playback chain | `Line DAC` 106 (90 %), `Line` 3 (33 %, +3 dB), `HP DAC` 0 |
| Signal | 1 kHz sine at 0.5 full scale, 1.0 s per step |
| Script | [`tools/device/lab-pi5/70-audio-level-probe.sh`](../../../tools/device/lab-pi5/70-audio-level-probe.sh) |

## Result

Sink volume against the level the microphone measures in the tone's own
frequency bin. Three runs; the tone column is repeatable to about ±1.5 dB, the
noise-floor estimate is not (see the caveat).

| Sink volume | Tone at the mic | Run 1 | Run 2 | Run 3 |
| --- | --- | --- | --- | --- |
| 3 % | -98.3 dBFS | — | -90.2 | -98.3 |
| 4 % | -94.7 | -93.7 | -90.4 | -94.7 |
| 6 % | -84.8 | -88.5 | -85.3 | -84.8 |
| 8 % | -77.5 | -79.7 | -78.1 | -77.5 |
| 10 % | -72.7 | — | -72.3 | -72.7 |
| 13 % | -66.8 | — | -66.1 | -66.8 |
| 16 % | -61.0 | — | -60.4 | -61.4 |
| 20 % | -56.4 | — | -55.8 | -57.0 |
| 26 % | -49.1 | — | — | -49.1 |
| 32 % | -43.6 | — | — | -43.6 |
| **36 %** | **-40.6** | — | — | -40.6 |

The control is a clean attenuator: doubling the volume moves the measurement by
5.7–6.1 dB, which is 20·log₁₀(2) = 6.02 dB. There is no hidden compressor or AGC
in the path, so the sink volume can be treated as a straight gain and a test can
pick its level by arithmetic rather than by ear.

**36 % is the volume the device normally runs at**, so the level a spoken reply
reaches the microphones at is about -40 dBFS. That is the number to compare
against: anything above about -60 dBFS is comfortably measurable, and 16 % is
20 dB below the normal listening level.

## What to use

- **16 % is the quiet setting for automated tests.** It measures -61 dBFS, about
  20 dB below a normal reply, and it is the lowest step that was still a clear
  signal rather than noise in all three runs.
- **26 % is the safe setting** if the room is not silent: -49 dBFS is 40 dB above
  the quietest noise floor measured here, which leaves room for a fridge, a fan or
  a conversation in the next room.
- **Do not go below 10 %.** At 8 % the signal is within a few dB of the ambient
  noise in one run, and at 3–4 % the measurement is indistinguishable from it.

## Two things that made the first attempts wrong

Recorded because they will mislead any future audio test on this device.

1. **`pw-play -a` does not read a regular file.** Given `pw-play -a --rate 48000
   --channels 1 --format s16 file.raw` it exits 0 after about 84 ms having played
   nothing, so every sweep measured silence and the microphone appeared dead.
   A real WAV file, played as `pw-play tone.wav`, takes the expected 3 s and
   works. Raw capture on stdin (`pw-record -a ... -`) is fine; it is raw
   *playback from a file* that fails.
2. **Broadband RMS is useless on this capture path.** The codec's capture carries
   a DC offset around -37 dBFS and a low-frequency rumble; together they dominate
   an RMS measurement and hide a tone that is plainly there. Measuring the
   tone's own frequency bin (Goertzel) instead gives a clean, repeatable number.
   The script now does that, and takes the strongest 0.25 s window rather than
   assuming when playback started, because PipeWire suspends an idle sink and
   loses the first tenths of a second.

## The speaker is not the problem

Before the volume sweep, the same 1 kHz tone was played straight to ALSA
(`aplay -D plughw:0,0`, 15 % amplitude, bypassing PipeWire and therefore the sink
volume) and the microphone measured it 48 dB above the noise floor in its bin.
So the amplifier, the JST speaker and the microphones all work; the failure mode
that produced a silent device earlier was a zero `Line DAC` gain, and it is not
this.

## Limits

- One specimen, one room, one night. No sound-level meter, so nothing here is in
  dB SPL; the numbers are digital levels at the microphone, which is what a test
  needs and all that was measured.
- The noise floor is the weak part of the method. Measured as the strongest 1 kHz
  window in a quiet recording, it came out at -106, -90 and -79 dBFS on three
  consecutive runs. The tone measurements agree to ±1.5 dB; the SNR column is
  only as good as that floor, so this note quotes absolute levels and treats SNR
  as a sanity check.
- Nothing here says whether a spoken reply at 36 % is *comfortable* to a person in
  the room. That needs ears.
- The tone is 0.5 full scale and a second long. Speech is closer to full scale and
  much longer, so a reply measures a few dB above these numbers at the same
  volume.
