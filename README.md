# Notes on building and setting up a Home Assistant Local Voice Assistant.

## Prebuilt Solutions

| Device                                                                              | Notes                                                                                                                         | Cost                                                                                                | Functions          | TODO                                                             |
|-------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|--------------------|------------------------------------------------------------------|
| [Atom Echo](https://www.home-assistant.io/voice_control/thirteen-usd-voice-remote/) | EXTREMELY quiet speaker.  Acceptable as microphone-only and development.<br/> Minimal specs causing issue in ESP Home updates | [$14](https://shop.m5stack.com/products/atom-echo-smart-speaker-dev-kit)                            | Voice              |                                                                  |
| Atom EchoS3R                                                                        | Assumed significantly better than the base Atom Echo                                                                          | [$15](https://shop.m5stack.com/products/atom-echos3r-smart-speaker-dev-kit?variant=46751279710465)  | Voice              | Need to test.<br/>Expected fixed updates and better speaker/mic. |
| [Home Assistant Voice PE](https://www.home-assistant.io/voice-pe)                   | Generally poor quality speaker for the price.  Native device with priority support/development - though less open/clear (?).  | $69                                                                                                 | Voice<br/>SendSpin |                                                                  |

## "Custom" Hardware
A "custom" solution may generally be preferred.  Price to performance should be considerably better at ~\$35-50 per device (less if parts are already had).  Being Linux based, it'll be more flexible.  For example, a monitor can be hooked up as a home display or camera feed or an LCD module like the [LCD1602](https://www.amazon.com/dp/B0BV6NCJBM) as a basic clock.

### Platforms
| Device                                                             | Notes                                                                                                                                         | Cost | Functions                                         |
|--------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|------|---------------------------------------------------|
| [Raspberry Pi 0 V1](https://rpilocator.com/?country=US&cat=PIZERO) | Linux-Voice-Assistant is capping CPU, needs resolved or configure as streaming, but almost (...) working<br/>RasPi OS Lite's wifi is broken.  | $16  | SnapCast<br/>SendSpin                             |
| [Raspberry Pi 02](https://rpilocator.com/?country=US&cat=PIZERO2)  | Target device.  Less frequently in stock.                                                                                                     | $20  | Voice<br/>SnapCast<br/>SendSpin                   |
|                                                                    |                                                                                                                                               |      |                                                   |

### Speakers


| Device                                               | Notes                                                                           | Cost  |
|------------------------------------------------------|---------------------------------------------------------------------------------|-------|
| [701715519671](https://www.amazon.com/dp/B0B4D1BN4F) | Minimal footprint                                                               | $2.50 |
| [701715519664](https://www.amazon.com/dp/B0B4D2Z35P) | Effectively the same size as the Pi-Zero.  Negligible better sound              | $2.50 |
| [701715520462](https://www.amazon.com/dp/B0BHST51PQ) | Significantly better audio than the other `DWEII` speakers, though much larger. | $3.50 |

### Audio Driver

| Device                                                                                   | Notes                                                                                                                                                                     | Cost                                                             |
|------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------|
| [Waveshare WM8960 Audio Hat](https://www.waveshare.com/wm8960-audio-hat.htm)             | Arrives with Stereo version of the [701715520462](https://www.amazon.com/dp/B0BHST51PQ)<br/>Has male header pins, allowing for an added screen or other added above.      | [$19](https://www.waveshare.com/wm8960-audio-hat.htm)            |
| Keyestudio ReSpeaker                                                                     | ReSpeaker V1                                                                                                                                                              | [$8](https://www.aliexpress.us/item/2251832715986197.html)       |
| [reSpeaker 2-Mics Pi HAT V2.0](https://www.seeedstudio.com/ReSpeaker-2-Mics-Pi-HAT.html) | ReSpeaker V2.  [Distinguish V1 from V2.](https://wiki.seeedstudio.com/how-to-distinguish-respeaker_2-mics_pi_hat-hardware-revisions/).  Advertises higher quality output. | [$14](https://www.seeedstudio.com/ReSpeaker-2-Mics-Pi-HAT.html)  |

### Cases
TODO: Cases for Pi/Driver combos to be created and uploaded - or linked


### Software Components

#### Base OS
- [Raspian / Raspberry Pi OS](https://www.raspberrypi.com/software/)

#### Music Client / Receiver
A key expectation for a home speaker system is the ability to play music **in sync** across multiple devices.

#### [SnapCast Client](https://github.com/snapcast/snapcast)
- Setup/Configured with the script [TODO]()
- Older, mature platform.
- TODO: Does it allow for delay adjustments?
- Unsupported:
  - Home Assistant Voice PE
  - ESP32-based devices
  - Non-Debian Linux Distros

#### [SendSpin](https://www.music-assistant.io/player-support/sendspin/)
- Has a Python implementation so it should generally be cross-platform.
- Unsupported:
  - ESP32-based devices (yet?  It's supported on HA Voice PE)
  - Android Client (yet.  Python solution made with AI Slop should be quickly spun up)

### Voice Assistant

#### [Linux Voice Assistant](https://github.com/OHF-Voice/linux-voice-assistant)
Interfaces via ESPHome protocol to Home Assistant.

#### [Wyoming](https://github.com/rhasspy/wyoming-satellite) (deprecated)

---

---

---

# Old Docs

#### Budget (untested)
| Device                                                                      | Ideal Cost  |
|-----------------------------------------------------------------------------|-------------|
| [Raspberry Pi 0W](https://www.raspberrypi.com/products/raspberry-pi-zero-w) | $16         |
| [ReSpeaker 2-Mic](https://www.aliexpress.us/item/2251832715986197.html)     | $8          |
| [MicroSD](https://www.aliexpress.us/item/3256810200208932.html)             | $3          |
| Case                                                                        | $1          |
| [Speaker](https://www.amazon.com/gp/product/B0BTP67F81)                     | $3          |
| USB Charger and MicroUSB cord                                               | $3          |
| --------------------------------------------------------------------------- | ----------- |
| **Total**                                                                   | **$34**     |
 

#### Typical
| Device                                                                                     | Ideal Cost   |
|--------------------------------------------------------------------------------------------|--------------|
| [Raspberry Pi 02W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/)            | $20          |
| [reSpeaker 2-Mics Pi HAT V2.0](https://www.seeedstudio.com/ReSpeaker-2-Mics-Pi-HAT.html)   | $14          |
| [MicroSD](https://www.amazon.com/TEAMGROUP-Micro-UHS-I-SDHC-SDXC/dp/B09WRJJ419/ )          | $5           |
| Case                                                                                       | $1           |
| [Speaker](https://www.amazon.com/dp/B0BHST51PQ)                                            | $4           |
| USB Charger and MicroUSB cord                                                              | $3           |
| ------------------------------------------------------------------------------------------ | ------------ |
| **Total**                                                                                  | **$47**      |

Notes:
1. The Raspberry Pi 0W is untested, but should (hopefully) work with the shift from Wyoming to Linux-Voice-Assistant.
2. It seems the [reSpeaker 2-Mics Pi HAT V2.0](https://www.seeedstudio.com/ReSpeaker-2-Mics-Pi-HAT.html) is supposedly higher audio quality for $14 ($12 bulk) instead.