"""The audio boards this repository has evidence for, and how to install one.

Two programs read this table and they must agree: the web page, which reports
what is fitted and offers the Install button, and `control/setup/hat_install.py`,
which runs as root and is the only thing that ever writes the boot
configuration. Keeping one table is the point — a second copy in the root helper
would be a second answer to "which overlay is this board", and the copy that
writes the file is not the one a reviewer reads on the page.

The install fields are deliberately separate from the recognition fields. What a
board *is* (how its EEPROM product string reads, which ALSA card it creates) is
evidence from the device. What installing it *means* (which overlay, which
kernel module, whether I2C has to be on) is a fact about the image, and each
entry says how well that fact is established. `install_note` is shown to the
person pressing the button, so it has to be honest about what has not been
proven.
"""

# The audio hardware this repository has evidence for, and how to recognise it.
# `match` needs a vendor word and a two-microphone model word, both present in
# the device-tree HAT EEPROM product. One word alone is not recognition: an
# earlier test matched any product containing "seeed" or "respeaker", so a
# ReSpeaker 4-mic array and an unrelated Seeed sensor HAT were both reported as
# this exact board. Even a full match establishes the *family*, not the model or
# revision. `card` is the ALSA card name the tested overlay creates. Neither
# proves a working microphone.
HAT_OPTIONS = (
    {"id": "respeaker-2mic-hat-v2",
     "label": "ReSpeaker 2-Mics Pi HAT v2",
     "summary": "TLV320AIC3104 codec, two microphones, three APA102 LEDs, a user button, "
                "3.5 mm and JST speaker outputs.",
     "match": {"vendor": ("respeaker", "seeed"),
               # Matched as a pattern, with a number boundary either side of the
               # 2: plain substring matching read `2-mic` inside `12-Mics` and
               # reported a twelve-microphone board as this two-microphone one.
               # `2-microphone` is the same board described in full.
               "model": (r"(?<![0-9])2[-\s]?(?:mics?|microphones?)(?![a-z0-9])",)},
     "card": "seeed2micvoicec",
     # The in-tree overlay the Raspberry Pi kernel ships for this board. It is
     # the one the lab Pi 5 boots with today.
     "overlay": "respeaker-2mic-v2_0",
     "needs_i2c": True,
     "modules": ("snd-soc-tlv320aic3x",),
     "install_note": "This uses the Raspberry Pi kernel's own respeaker-2mic-v2_0 "
                     "overlay. It names the tlv320aic3x driver, while the v2 board "
                     "carries a TLV320AIC3104; it binds on the Pi 5 here, but that "
                     "family mismatch is unresolved and on the 32-bit Zero W image "
                     "the module is absent, which this refuses rather than guesses "
                     "around.",
     "caveats": (
         "Microphone and LED positions are an estimate, not a measurement of this board: "
         "they come from Seeed's v1 Eagle layout plus a photograph cross-check, and a v2 "
         "board could have moved a part. Heights are unmeasured.",
         "The LEDs (APA102 on SPI) and the button (GPIO17) are not audio: no audio driver "
         "provides them.",
     )},
    {"id": "respeaker-2mic-hat-v1",
     "label": "ReSpeaker 2-Mics Pi HAT v1",
     "summary": "The earlier Seeed board: a WM8960 codec, two microphones, 3.5 mm and "
                "screw-terminal speaker outputs, and a user button.",
     # Nothing here can read the revision. Seeed's EEPROM product string for the
     # 2-Mics HAT does not carry one, and the difference between the revisions is
     # the codec (WM8960 here, TLV320AIC3104 on v2), which this page does not
     # interrogate. Claiming a match from the product name alone would report
     # both revisions as present at once.
     "match": (),
     "card": "wm8960soundcard",
     "overlay": "wm8960-soundcard",
     "needs_i2c": True,
     "modules": ("snd-soc-wm8960",),
     "install_note": "This is the overlay that was measured on this hardware: a Zero 2 "
                     "W with a Seeed v1 board, after which the wm8960soundcard card "
                     "bound on the first attempt. The codec binds without regulator "
                     "control (dummy regulators), so its supplies are not managed.",
     "caveats": (
         "The WM8960 card being present is the only evidence this page has, and it "
         "cannot name which board bound it.",
         "The one device that bound this board used the in-tree "
         "`wm8960-soundcard` overlay with dummy regulators, so the codec's supplies "
         "are not controlled by that driver.",
     )},
    {"id": "waveshare-wm8960",
     "label": "Waveshare WM8960 Audio HAT",
     "summary": "Waveshare's WM8960 board: two MEMS microphones, 3.5 mm output and "
                "screw terminals for the speakers it ships with.",
     # A WM8960 codec does not name its vendor. Presenting a WM8960 card as proof
     # of this board would equally be proof of the Seeed v1 HAT above.
     "match": (),
     "card": "wm8960soundcard",
     "overlay": "wm8960-soundcard",
     "needs_i2c": True,
     "modules": ("snd-soc-wm8960",),
     "install_note": "wm8960-soundcard is Waveshare's own documented overlay and the "
                     "in-tree driver. It was measured here with a Seeed v1 board, not "
                     "with this one; the two boards share a codec, not a proven pinout.",
     "caveats": (
         "A WM8960 card is consistent with this board and with the Seeed v1 HAT; "
         "the driver does not say which one is fitted.",
         "Waveshare sells several audio HATs. The vendor name does not identify a "
         "model, a revision or its driver.",
     )},
    {"id": "none",
     "label": "No HAT: 3.5 mm jack or USB audio",
     "summary": "The board's own headphone output, or a USB sound card.",
     "match": (),
     "card": None,
     # Not a board: installing "none" means removing any overlay this table
     # manages, which is the honest way to undo one of the others.
     "overlay": None,
     "needs_i2c": False,
     "modules": (),
     "install_note": "This removes any audio-HAT overlay this page manages from the "
                     "boot configuration. It does not remove the overlay files or any "
                     "driver from the image, and it does not change the running system "
                     "until the device restarts.",
     "caveats": (
         "This page cannot tell which output is in use; the Audio card names the selected sink.",
     )},
)

# The overlays this table is allowed to add or remove. Any `dtoverlay=` line for
# one of these is managed; every other line in config.txt is left exactly as it
# is, so the graphics driver, the USB mode and anything a person added by hand
# survive an install.
MANAGED_OVERLAYS = tuple(sorted({option["overlay"] for option in HAT_OPTIONS
                                 if option["overlay"]}))
BOARD_IDS = tuple(option["id"] for option in HAT_OPTIONS)


def option(board_id):
    """The table entry for one id, or None. Never guesses a near match."""
    for entry in HAT_OPTIONS:
        if entry["id"] == board_id:
            return entry
    return None


def card_for(board_id):
    """The ALSA card a board creates, or None for a board that creates none."""
    entry = option(board_id)
    return entry["card"] if entry else None
