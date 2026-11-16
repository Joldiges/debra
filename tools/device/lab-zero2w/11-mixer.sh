#!/bin/sh
# Seeed ReSpeaker 2-Mics Pi HAT v1 (WM8960) mixer for PipeWire use.
#
# Measured on debra-8518d6, 2026-11-16, ambient room noise at 16 kHz stereo:
#   capture PGA at max (+30 dB, value 63), ADC digital 0 dB (value 195)
#       -> peak 229-247, RMS 38   (about -42 dBFS)
#   Input Mixer Boost on (any LINPUT1 boost volume 0-3)
#       -> peak 3.4k-32k, RMS 275-1675: clips on room noise alone, so OFF
#   ADC PCM 225 (+15 dB digital)
#       -> peak 1460, RMS 221: too hot for speech peaks
#   ADC High Pass Filter on
#       -> peak 238 with RMS 216: a near-constant full-scale offset instead of
#          DC removal. Recorded as a suspicion, not diagnosed; left OFF.
#
# The gain is a starting point. If wake-word or STT performance is poor, try
# MIC_AUTO_GAIN=1 in the LVA unit before changing codec gain again.
set -eu
export PATH=/usr/sbin:$PATH
C=wm8960soundcard

set_numid() { amixer -c "$C" cset "numid=$1" "$2" >/dev/null; }

# Capture: PGA at maximum (+30 dB) and unity digital. The PGA is the analog
# stage, so all of the gain is applied where it costs least noise.
set_numid 1 63        # Capture Volume
set_numid 3 on        # Capture Switch
set_numid 36 195      # ADC PCM Capture Volume (0 dB digital)
set_numid 19 off      # ADC High Pass Filter
set_numid 26 0        # ALC Function: off

# Route the microphones into the PGA and leave the boost stage out of it.
amixer -c "$C" sset 'Left Boost Mixer LINPUT1' on >/dev/null
amixer -c "$C" sset 'Right Boost Mixer RINPUT1' on >/dev/null
amixer -c "$C" sset 'Left Boost Mixer LINPUT2' off >/dev/null
amixer -c "$C" sset 'Right Boost Mixer RINPUT2' off >/dev/null
amixer -c "$C" sset 'Left Boost Mixer LINPUT3' off >/dev/null
amixer -c "$C" sset 'Right Boost Mixer RINPUT3' off >/dev/null
set_numid 9 0         # Left Input Boost Mixer LINPUT1 Volume
set_numid 8 0         # Right Input Boost Mixer RINPUT1 Volume
amixer -c "$C" sset 'Left Input Mixer Boost' off >/dev/null
amixer -c "$C" sset 'Right Input Mixer Boost' off >/dev/null

# Playback. The overlay leaves the DAC disconnected from every output mixer, so
# the card was silent with a healthy service and a moving volume slider: a tone
# played to the sink produced no 1 kHz energy at the HAT's own microphone.
#
# Measured 2026-11-16 with a 1 kHz tone at 40% sink volume, recording from the
# HAT and computing energy at 1 kHz against a 1.5 kHz control:
#   output mixer PCM off                      -> ratio 2.6   (nothing)
#   output mixer PCM on, headphone 70/127     -> ratio 26    (nothing)
#   the above plus Speaker DC/AC at 5         -> ratio 7812, peak 326 (the tone)
# So this board's speaker is on the WM8960 class-D output, not the headphone
# path. Both are left enabled: the 3.5 mm jack is otherwise silently dead.
set_numid 10 215      # Playback Volume (the overlay's default, retained)
set_numid 52 on       # Left Output Mixer PCM Playback Switch
set_numid 55 on       # Right Output Mixer PCM Playback Switch
set_numid 15 5        # Speaker DC Volume
set_numid 16 5        # Speaker AC Volume
set_numid 11 70       # Headphone Playback Volume (jack; not the speaker path)

sudo alsactl store
echo "stored mixer state for $C"
for n in 1 36; do amixer -c "$C" cget numid=$n | tail -1; done
