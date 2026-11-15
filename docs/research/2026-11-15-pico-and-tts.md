# Pico support boundaries and Home Assistant speaking speed

**Upstream-source review, 2026-11-15; no device or household-provider test.**
Prepared by coordinator `openai/gpt-6.1-sol`, variant unknown, from the earlier
WEB-R01 research and separate WEB-R02 source review by `openai/gpt-6.1-sol`,
variant unknown. Same-model fresh-session review is useful corroboration, not
fully independent empirical evidence. No firmware choice or provider change.

## Pico is not a small Linux Pi

| Claim | Evidence / scope |
| --- | --- |
| LVA uses the ESPHome protocol but is a full-Linux application, not RP2040/RP2350 firmware | [LVA v1.1.18 README](https://raw.githubusercontent.com/OHF-Voice/linux-voice-assistant/v1.1.18/README.md); documented AMD64/AArch64 baseline |
| General RP2 board support includes Pico W and Pico 2 W | [ESPHome RP2](https://esphome.io/components/rp2/), mutable docs displaying 2026.10.2 when reviewed |
| ESPHome Sendspin requires ESP32 with ESP-IDF | [Sendspin component](https://esphome.io/components/sendspin/), same documentation version/date |
| ESPHome I²S audio requires ESP32 | [I²S audio](https://esphome.io/components/i2s_audio/); that page alone does not establish ESP-IDF-only support |

**Inference:** Pico W/Pico 2 W are not a currently documented upstream
voice-plus-Sendspin replacement along this pathway. This does **not** prove it is
physically impossible or that no third-party implementation exists. ESP32-S3 is
a separate candidate tier, not a verified complete product/BOM or an assumed
ReSpeaker-HAT-compatible substitute. Original Pi Zero W remains a full-support
engineering goal.

## Speaking rate follows the actual TTS provider

Home Assistant may use different providers for conversation, STT and TTS. An
OpenAI conversation agent does not establish that OpenAI generates the voice.

- **OpenAI TTS:** the [HA OpenAI options](https://www.home-assistant.io/integrations/openai_conversation/#options)
  document **Speed 0.25–4.0, default 1.0** for TTS subentries. Use Settings →
  Devices & services → the relevant OpenAI instance/TTS subentry options →
  Speed. Generic cogwheel navigation is documented; the household UI was not
  inspected. Don't change conversation-agent options expecting speech rate.
- **Generic TTS audio settings:** [`preferred_sample_rate`](https://www.home-assistant.io/integrations/tts/#preferred-audio-settings)
  is encoding/transcoding in Hz, not speaking speed. HA docs displayed 2026.11.1.
- **Piper/Wyoming correction:** absence of a README setting does not mean there
  is no rate-related control. At `wyoming-piper v1.6.3`,
  [`__main__.py`](https://raw.githubusercontent.com/rhasspy/wyoming-piper/v1.6.3/wyoming_piper/__main__.py)
  defines `--length-scale` (“Phoneme length”), and
  [`process.py`](https://raw.githubusercontent.com/rhasspy/wyoming-piper/v1.6.3/wyoming_piper/process.py)
  forwards it to Piper. This is a server-startup control, not evidence of an HA
  slider or a per-request option.
- [HA Wyoming docs](https://www.home-assistant.io/integrations/wyoming/) show no
  speed setting. The
  [HA Core 2026.11.1 implementation](https://raw.githubusercontent.com/home-assistant/core/2026.11.1/homeassistant/components/wyoming/tts.py)
  exposes audio output, voice and speaker, not speed/length-scale. A particular
  Piper app/container can expose its own startup configuration; that packaging
  remains unverified.

## Next evidence needed

Identify the affected Assist pipeline's **TTS entity/provider and HA version**;
if Piper, also its deployment type and version. Then give instructions for that
actual deployment. No provider changes or speaking tests have been made.
