#!/bin/sh
# ReSpeaker 2-Mics Pi HAT v2.0 (TLV320AIC3104) mixer for PipeWire use.
# Codec at unity gain; loudness is controlled by PipeWire, not the codec.
# Capture: 12 dB PGA (the driver default is +16 dB and clips), AGC off, Line1
# only (the microphones are wired to LINE1L/LINE1R; MIC2 is unconnected).
set -eu
export PATH=/usr/sbin:$PATH
C=seeed2micvoicec

set_ctl() { amixer -c "$C" cset name="$1" "$2" >/dev/null; }

set_ctl 'PGA Capture Volume' 24
set_ctl 'PGA Capture Switch' on
set_ctl 'AGC Switch' off
for side in Left Right; do
  set_ctl "$side PGA Mixer Line1L Switch" off
  set_ctl "$side PGA Mixer Line1R Switch" off
  set_ctl "$side PGA Mixer Mic2L Switch" off
  set_ctl "$side PGA Mixer Mic2R Switch" off
done
set_ctl 'Left PGA Mixer Line1L Switch' on
set_ctl 'Right PGA Mixer Line1R Switch' on

set_ctl 'PCM Playback Volume' 0dB
set_ctl 'HP DAC Playback Volume' 0dB
set_ctl 'HP Playback Switch' on
set_ctl 'Line DAC Playback Volume' 0dB
set_ctl 'Line Playback Switch' on

sudo alsactl store
echo "stored mixer state for $C"
amixer -c "$C" cget name='PGA Capture Volume' | tail -1
amixer -c "$C" cget name='PCM Playback Volume' | tail -1
