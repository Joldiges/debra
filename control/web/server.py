"""Small, LAN-only Debra control prototype; Python standard library only.

This is not an internet-facing administration server. It runs as the audio
session user, never uses sudo, and exposes only volume/mute writes.
"""

import argparse
from contextlib import contextmanager
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import socket
import stat
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlsplit

if __package__:
    from . import discovery
else:
    import discovery


ASSETS = Path(__file__).with_name("assets")
STATIC = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
          "/style.css": ("style.css", "text/css")}
SERVICES = (
    ("Linux Voice Assistant", "linux-voice-assistant.service", True),
    ("Sendspin", "sendspin.service", True),
    ("Snapcast (user)", "snapclient.service", True),
    ("Snapcast (system)", "snapclient.service", False),
    ("PipeWire", "pipewire.service", True),
    ("WirePlumber", "wireplumber.service", True),
)
# The audio hardware this repository has evidence for, and how to recognise it.
# `match` needs a vendor word and a two-microphone model word, both present in
# the device-tree HAT EEPROM product. One word alone is not recognition: the
# previous test matched any product containing "seeed" or "respeaker", so a
# ReSpeaker 4-mic array and an unrelated Seeed sensor HAT were both reported as
# this exact board. Even a full match establishes the *family*, not the model or
# revision. `card` is the ALSA card name the tested overlay creates. Neither
# proves a working microphone, and no write exists to change either.
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
     "caveats": (
         "Microphone and LED positions are an estimate, not a measurement of this board: "
         "they come from Seeed's v1 Eagle layout plus a photograph cross-check, and a v2 "
         "board could have moved a part. Heights are unmeasured.",
         "The LEDs (APA102 on SPI) and the button (GPIO17) are not audio: no audio driver "
         "provides them.",
     )},
    {"id": "none",
     "label": "No HAT: 3.5 mm jack or USB audio",
     "summary": "The board's own headphone output, or a USB sound card.",
     "match": (),
     "card": None,
     "caveats": (
         "This page cannot tell which output is in use; the Audio card names the selected sink.",
     )},
)
REQUEST_TIMEOUT = 15
COMMAND_TIMEOUT = 2
DISCOVERY_INTERVAL = 30


class DiscoveryCache:
    def __init__(self, browse=discovery.browse, interval=DISCOVERY_INTERVAL):
        self.browse, self.interval = browse, interval
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.devices = ()
        self.last_scan = None      # monotonic; None means no scan has finished yet
        self.last_error = None
        # One entry per refused record the scan returned, as "name: reason".
        # Reasons are what a person needs, and the count is records, which is
        # what the page says it is. Keeping only the display string merged two
        # different devices that happened to be refused for the same reason.
        self.refused = ()
        self.thread = None

    def scan(self):
        # Each entry is (identity, "name: reason"). The parser reports one
        # refusal per record it dropped but carries only the instance name and
        # the reason, and two records can share both (one port 0 and one port
        # 65536, for example), so its position in the reported list is the
        # identity that survives. This hub's own revalidation still has the
        # record, so it is keyed by the name and URL it refused and a repeated
        # scan cannot multiply it. The limits are honest: avahi reports a
        # resolved record once per interface and address family, so one refused
        # advertisement seen twice is counted twice, and two malformed records
        # with the same name and URL merge into one entry. The count is
        # therefore refused records, not proven distinct advertisements, and
        # the page says so. A count that can be high is better than silently
        # dropping a device from the page.
        refused = []

        def note(identity, name, reason):
            entry = (identity, f"{name}: {reason}")
            if entry not in refused:
                refused.append(entry)

        try:
            result = self.browse()
            if not isinstance(result, dict) or result.get("error") is not None:
                devices = ()
            else:
                # The parser drops records before this hub ever sees them. Its
                # reasons have to travel with the result, or the page reports a
                # successful empty scan while an advertisement was rejected.
                reported = result.get("refused")
                if isinstance(reported, list):
                    for index, entry in enumerate(reported):
                        if (isinstance(entry, dict) and isinstance(entry.get("name"), str)
                                and isinstance(entry.get("reason"), str)):
                            note(("parser", index), entry["name"], entry["reason"])
                        else:
                            raise ValueError("Invalid discovery refusal")
                records = result["devices"]
                if not isinstance(records, list):
                    raise ValueError("Invalid discovery result")
                valid = []
                for record in records:
                    item, reason = discovery.accept_record(record)
                    if reason is None:
                        valid.append(dict(item, source="discovered"))
                    else:
                        # Revalidation is this hub's own boundary: the parser's
                        # warning never reaches this page, so name the reason
                        # here or the drop is silent.
                        # A record can be any JSON value, None included, so
                        # the name is read defensively: an AttributeError here
                        # would empty the whole list instead of refusing one.
                        name = record.get("name") if isinstance(record, dict) else None
                        url = record.get("url") if isinstance(record, dict) else None
                        note(("hub", name, url), name or "unnamed", reason)
                        discovery.LOGGER.warning("Refused discovered record: %s", reason)
                devices = tuple(valid)
        except Exception:
            # A broken discovery implementation must not take down the page.
            devices = ()
            result = {"error": "discovery failed"}
        with self.lock:
            self.devices = devices
            self.last_scan = time.monotonic()
            self.refused = tuple(sorted(text for _, text in refused))
            self.last_error = (result or {}).get("error") if isinstance(result, dict) else None

    def snapshot(self):
        with self.lock:
            return self.devices

    def status(self):
        """What the page needs to say whether discovery is actually working.

        A thread object outlives the thread, so liveness is asked of the thread
        itself: a worker that died after starting must not look healthy.
        """
        with self.lock:
            thread = self.thread
            alive = thread is not None and thread.is_alive()
            age = None if self.last_scan is None else max(0, time.monotonic() - self.last_scan)
            error = self.last_error
            if thread is not None and not alive and not self.stop.is_set() and error is None:
                error = "Discovery worker stopped unexpectedly"
            return {"enabled": alive, "found": len(self.devices),
                    "seconds_since_scan": None if age is None else round(age),
                    "error": error, "refused": list(self.refused)}

    def run(self):
        try:
            while not self.stop.is_set():
                self.scan()
                if self.stop.wait(self.interval):
                    break
        except Exception as exc:
            # Record the exit instead of leaving a dead thread looking healthy.
            with self.lock:
                self.last_error = f"Discovery worker stopped ({type(exc).__name__}: {exc})"

    def start(self):
        try:
            self.thread = threading.Thread(target=self.run, daemon=True, name="debra-discovery")
            self.thread.start()
        except (OSError, RuntimeError) as exc:
            # Resource exhaustion must not prevent configured links being served.
            with self.lock:
                self.thread = None
                self.last_error = f"Discovery thread could not start ({type(exc).__name__}: {exc})"


def merge_devices(configured, discovered):
    """Configured first, one row per URL, and a device found both ways says both.

    Collapsing a discovered device into a quiet "configured" row is what made a
    working discovery look like a hand-written list.
    """
    result, index = [], {}
    for device in configured:
        # A hand-written file can repeat a URL; the first entry still wins.
        if device["url"] not in index:
            entry = dict(device, source="configured")
            index[entry["url"]] = len(result)
            result.append(entry)
    for device in discovered:
        url = device["url"]
        if url in index:
            # Only a configured row can become "both"; two discovered records for
            # one URL are one discovered device, not a configured one.
            if result[index[url]]["source"] == "configured":
                result[index[url]]["source"] = "configured+discovered"
        else:
            index[url] = len(result)
            result.append(dict(device, source="discovered"))
    return result


class Unavailable(Exception):
    """A probe/control failed; raw command output must not reach the browser."""


class RequestExpired(TimeoutError):
    """The overall request budget expired; do not begin any more commands."""


def remaining(deadline):
    budget = deadline - time.monotonic()
    if budget <= 0:
        raise RequestExpired("Request deadline expired")
    return budget


def run_command(argv, *, timeout=COMMAND_TIMEOUT):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Unavailable("Command unavailable or timed out") from exc
    if result.returncode:
        raise Unavailable("Command did not succeed")
    return result.stdout


def read_text(root, name):
    try:
        return (root / name.lstrip("/")).read_text().strip().strip("\0")
    except (OSError, UnicodeError):
        return ""


def read_optional(root, name):
    """Read a kernel file, keeping "unreadable" apart from "empty".

    `read_text` collapses both to "", which would turn a permission failure into
    a confident "nothing is there" — the one answer a setup page must not invent.
    """
    try:
        return (root / name.lstrip("/")).read_text()
    except (OSError, UnicodeError):
        return None


CARD_LINE = re.compile(r"^\s*\d+\s+\[([^]]+)\]")


def hat_family_match(product, option):
    """Whether an EEPROM product string names this option's hardware family.

    A family match is all this can establish. Two independent words are
    required - one vendor and one model - so a different ReSpeaker board or an
    unrelated Seeed HAT is not reported as this one. Each vendor word has to
    stand on its own: a substring match read `respeaker` inside `NotReSpeaker`
    and `seeed` inside `Unseeeded`, which made any string containing those
    letters this family. The revision is still unknown: nothing this page reads
    establishes one.

    An option with no `match` (the alternative below) is not a board the EEPROM
    could name, so this is never the question to ask about it: `None` here.
    """
    match = option.get("match") or {}
    vendor = match.get("vendor") or ()
    model = match.get("model") or ()
    if not vendor or not model:
        return None
    words = (product or "").lower()

    def names_vendor(word):
        # A vendor word has to stand on its own. A plain substring matched
        # `respeaker` inside `NotReSpeaker` and `seeed` inside `Unseeeded`, so an
        # unrelated board was reported as this family. Letters and digits are
        # the boundary; an underscore or hyphen is not one, so `ReSpeaker_2-Mics`
        # and `seeed-2mic` still match.
        return re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])",
                         words) is not None

    return (any(names_vendor(word) for word in vendor)
            and any(re.search(word, words) for word in model))


def alsa_cards(root):
    """ALSA card ids from /proc/asound/cards, or None when it cannot be read."""
    text = read_optional(root, "/proc/asound/cards")
    if text is None:
        return None
    cards = []
    for line in text.splitlines():
        match = CARD_LINE.match(line)
        if match:
            cards.append(match.group(1).strip())
    return cards


def planned(identifier, label, summary, options, reason):
    """A choice the page can show but not make.

    Every setting is reported this way because the device has no config model to
    store one in yet: a value accepted and dropped would be worse than a visible
    control that says it is unavailable.
    """
    return {"id": identifier, "label": label, "summary": summary, "value": None,
            "options": options, "selectable": False, "reason": reason}


def finite_number(text, divisor=1):
    try:
        value = float(text) / divisor
        return value if math.isfinite(value) else None
    except ValueError:
        return None


def metrics(root, previous=None, elapsed=None):
    """Read unprivileged kernel counters. Missing data is null, never zero."""
    memory = {}
    for line in read_text(root, "/proc/meminfo").splitlines():
        key, _, value = line.partition(":")
        try:
            memory[key] = int(value.split()[0]) * 1024
        except (ValueError, IndexError):
            continue
    cpu = {}
    for line in read_text(root, "/proc/stat").splitlines():
        fields = line.split()
        if not fields or not re.fullmatch(r"cpu\d*", fields[0]):
            continue
        # guest/guest_nice are already included in user/nice, not extra time.
        try:
            counters = list(map(int, fields[1:9]))
            if len(counters) >= 4:
                cpu[fields[0]] = (sum(counters), counters[3] +
                                  (counters[4] if len(counters) > 4 else 0))
        except ValueError:
            continue
    usage = {}
    for name, (total, idle) in cpu.items():
        old = (previous or {}).get("cpu", {}).get(name)
        delta = total - old[0] if old else 0
        usage[name] = round(100 * max(0, min(delta, delta - (idle - old[1]))) /
                            delta, 1) if old and delta > 0 else None
    vm = {}
    for line in read_text(root, "/proc/vmstat").splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[0] in ("pswpin", "pswpout"):
            try:
                vm[fields[0]] = int(fields[1])
            except ValueError:
                continue
    swap_io = {}
    for name in ("pswpin", "pswpout"):
        old = (previous or {}).get("swap", {}).get(name)
        value = vm.get(name)
        swap_io[name + "_pages_per_s"] = (
            round((value - old) / elapsed, 2)
            if value is not None and old is not None and elapsed and value >= old
            else None
        )
    zram = []
    for device in sorted((root / "sys/block").glob("zram*")):
        try:
            values = list(map(int, (device / "mm_stat").read_text().split()))
            if len(values) >= 3:
                zram.append({"device": device.name, "original_bytes": values[0],
                             "compressed_bytes": values[1], "memory_bytes": values[2]})
        except (OSError, ValueError):
            continue
    wifi = []
    for line in read_text(root, "/proc/net/wireless").splitlines()[2:]:
        try:
            interface, data = line.split(":", 1)
            signal = finite_number(data.split()[2].rstrip("."))
            # Some drivers return unsigned/relative values, not signed dBm.
            wifi.append({"interface": interface.strip(),
                         "signal_dbm": signal if signal is not None and -127 <= signal <= 0 else None})
        except (ValueError, IndexError):
            continue
    def number(path, divisor=1):
        return finite_number(read_text(root, path), divisor)
    try:
        disk = shutil.disk_usage(root)
        storage = {"total_bytes": disk.total, "free_bytes": disk.free}
    except OSError:
        storage = None
    uptime = read_text(root, "/proc/uptime").split()
    data = {
        "model": read_text(root, "/sys/firmware/devicetree/base/model") or None,
        "detected_hat": read_text(root, "/sys/firmware/devicetree/base/hat/product") or None,
        "cpu_percent": usage, "memory": memory, "storage": storage,
        "temperature_c": number("/sys/class/thermal/thermal_zone0/temp", 1000),
        "uptime_s": finite_number(uptime[0]) if uptime else None,
        "wifi": wifi, "zram": zram, "swap_io": swap_io,
        "zswap_enabled": {"Y": True, "N": False}.get(
            read_text(root, "/sys/module/zswap/parameters/enabled")),
    }
    return data, {"cpu": cpu, "swap": vm}


class Backend:
    def __init__(self, sink, metadata, runner=run_command, root=Path("/")):
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.:-]*", sink):
            raise ValueError("Use an explicit native sink name, not a default alias")
        self.sink, self.metadata, self.runner, self.root = sink, metadata, runner, root
        self.lock = threading.Lock()
        self.previous = self.sample_time = self.cache_time = self.cached = None

    def command(self, argv, deadline=None):
        timeout = min(COMMAND_TIMEOUT, remaining(deadline)) if deadline is not None else COMMAND_TIMEOUT
        result = self.runner(argv, timeout=timeout)
        if deadline is not None:
            remaining(deadline)
        return result

    @contextmanager
    def acquired(self, deadline):
        if not self.lock.acquire(timeout=remaining(deadline)):
            raise RequestExpired("Backend wait expired")
        try:
            remaining(deadline)
            yield
        finally:
            self.lock.release()

    def audio(self, deadline=None):
        try:
            sinks = json.loads(self.command(["pactl", "--format=json", "list", "sinks"], deadline))
            sink = next(s for s in sinks if s["name"] == self.sink)
            channels = list(sink["volume"].values())
            percentages = [int(c["value_percent"].rstrip("%")) for c in channels]
            return {"available": True, "sink": self.sink,
                    "description": sink.get("description", self.sink),
                    "percent": max(percentages), "muted": sink["mute"],
                    "channel_percent": percentages}
        except (Unavailable, ValueError, KeyError, TypeError, AttributeError, StopIteration):
            return {"available": False, "sink": self.sink,
                    "error": "Selected output unavailable; no fallback was selected"}

    def change_audio(self, action, payload, deadline=None):
        deadline = time.monotonic() + REQUEST_TIMEOUT if deadline is None else deadline
        if action == "volume":
            value = payload.get("percent")
            if set(payload) != {"percent"} or type(value) is not int or not 0 <= value <= 100:
                raise ValueError("percent must be an integer from 0 to 100")
            argv = ["pactl", "set-sink-volume", self.sink, str(value) + "%"]
        elif action == "mute":
            value = payload.get("muted")
            if set(payload) != {"muted"} or type(value) is not bool:
                raise ValueError("muted must be true or false")
            argv = ["pactl", "set-sink-mute", self.sink, "1" if value else "0"]
        else:
            raise ValueError("Unknown action")
        with self.acquired(deadline):
            if not self.audio(deadline)["available"]:
                raise Unavailable("Selected output unavailable")
            # Recheck after both the lock wait and the availability probe. An
            # expired queued Apply must never invoke the native mutator.
            self.command(argv, deadline)
            return self.audio(deadline)

    def components(self, deadline=None):
        probes = {}
        for user in (True, False):
            units = [unit for _, unit, is_user in SERVICES if is_user == user]
            argv = ["systemctl"] + (["--user"] if user else []) + [
                "show", *units, "--property=Id,LoadState,ActiveState,UnitFileState"]
            try:
                for block in self.command(argv, deadline).strip().split("\n\n"):
                    properties = dict(line.split("=", 1) for line in block.splitlines()
                                      if "=" in line)
                    if properties.get("Id"):
                        probes[user, properties["Id"]] = properties
            except Unavailable:
                pass
        result = []
        for name, unit, user in SERVICES:
            properties = probes.get((user, unit))
            if properties:
                result.append({"name": name, "unit": unit,
                               "unit_found": properties.get("LoadState") == "loaded",
                               "active": properties.get("ActiveState"),
                               "enabled": properties.get("UnitFileState"),
                               "configuration": "Not yet inspected"})
            else:
                result.append({"name": name, "active": "unknown",
                               "configuration": "Probe unavailable"})
        result.extend([
            {"name": "Bluetooth proxy", "active": "unknown",
             "configuration": "No detector yet; Bluetooth hardware is not proof of a proxy"},
            {"name": "Music Assistant server", "active": "unknown",
             "configuration": "Server location/containers not inspected"},
        ])
        return result

    def power(self, deadline=None):
        output = {"throttle_flags": None, "supply_voltage_v": None}
        try:
            text = self.command(["vcgencmd", "get_throttled"], deadline).strip()
            if re.fullmatch(r"throttled=0x[0-9a-fA-F]+", text):
                flags = int(text.split("=")[1], 16)
                output.update(throttle_flags=hex(flags),
                              undervoltage_now=bool(flags & 1),
                              undervoltage_since_boot=bool(flags & (1 << 16)))
        except Unavailable:
            pass
        try:
            text = self.command(["vcgencmd", "pmic_read_adc"], deadline)
            match = re.search(r"\bEXT5V_V\s+\S+=([0-9.]+)V\b", text)
            if match:
                output["supply_voltage_v"] = finite_number(match[1])
        except Unavailable:
            pass
        return output

    def setup(self, deadline=None):
        """What this device is built to do, and why the page cannot change it.

        Read-only by design. A HAT change is a device-tree overlay and driver
        write, and there is no config model to record a setting in, so every
        choice is reported unavailable rather than accepted and dropped. This
        takes no backend lock: it reads no audio state and starts no write.
        """
        product = read_text(self.root, "/sys/firmware/devicetree/base/hat/product") or None
        cards = alsa_cards(self.root)
        options = []
        for option in HAT_OPTIONS:
            # "No HAT: 3.5 mm jack or USB audio" is an alternative, not a board:
            # asking the EEPROM about it and reporting "not named" stated the
            # exact opposite of the ReSpeaker row's evidence about the same
            # string, so `hat_family_match` reports nothing established for it.
            # The payload shape is unchanged: `detected` already has a null
            # "nothing established".
            detected = None if product is None else hat_family_match(product, option)
            present = None
            if option["card"] and cards is not None:
                present = option["card"] in cards
            options.append({
                "id": option["id"], "label": option["label"], "summary": option["summary"],
                "detected": detected,
                "card": {"name": option["card"], "present": present},
                # A listed card is the only evidence available here. It does not
                # prove capture, playback, or that the overlay survives a reboot.
                "applied": present,
                "caveats": list(option["caveats"]),
            })
        services = {row["name"]: row for row in self.components(deadline)}

        def observed(name):
            row = services.get(name) or {}
            return {"unit_found": row.get("unit_found"), "active": row.get("active"),
                    "enabled": row.get("enabled")}

        return {
            "writable": False,
            "reason": "This page reports what the device is built to do; it cannot change "
                      "any of it yet.",
            "hardware": {
                "detected_hat": product,
                "detected_source": "Device-tree HAT EEPROM product; empty means the HAT "
                                   "has no EEPROM or it is unreadable",
                "retained_label": self.metadata.get("hat") or None,
                "retained_note": "The retained label is a note from hardware.json, not a "
                                 "verified or applied choice.",
                "cards": cards,
                "cards_source": "/proc/asound/cards",
                "selectable": False,
                "reason": "Changing the HAT means writing a device-tree overlay and a driver "
                          "configuration, which nothing here can do (roadmap A02, WEB03).",
                "options": options,
            },
            "settings": {
                "music": planned(
                    "music", "Music player",
                    "Which receiver plays music on this device. SendSpin comes first; "
                    "Snapcast is the alternative.",
                    [{"id": "sendspin", "label": "SendSpin",
                      "observed": {"user": observed("Sendspin"), "system": None}},
                     {"id": "snapcast", "label": "Snapcast (alternative)",
                      "observed": {"user": observed("Snapcast (user)"),
                                   "system": observed("Snapcast (system)")}}],
                    "No music setting is stored on the device yet (roadmap C01), and neither "
                    "adapter can be installed or switched from here (M01, M03)."),
                "interruption": planned(
                    "interruption", "During an announcement",
                    "What happens to music when the device speaks.",
                    [{"id": "duck", "label": "Lower the music, then bring it back"},
                     {"id": "pause", "label": "Pause the music, then resume"}],
                    "Duck/resume and pause/resume are not implemented or tested on a device "
                    "yet (roadmap A03), and this page cannot control either music stack."),
                "update_policy": planned(
                    "update-policy", "Update policy", "How component versions change.",
                    [{"id": "pinned",
                      "label": "Pinned versions, updated by hand (the intended default)"},
                     {"id": "auto", "label": "Update a chosen component automatically"}],
                    "Debra has no update mechanism, version manifest or pinning policy of "
                    "its own yet (roadmap U01-U03), so there is no policy to record here. "
                    "Packages can of course still be changed by hand on the device."),
            },
            "updates": {
                "available": False,
                "reason": "No update, version manifest or snapshot/restore mechanism exists, "
                          "so none of these buttons can do anything.",
                "actions": [
                    {"id": "check", "label": "Check for updates", "enabled": False,
                     "reason": "There is no version manifest or update source to check "
                               "(roadmap U01)."},
                    {"id": "update", "label": "Install updates", "enabled": False,
                     "reason": "There is no update transaction to run (roadmap U02)."},
                    {"id": "rollback", "label": "Roll back the last change", "enabled": False,
                     "reason": "On-target snapshots and restore are not implemented (roadmap "
                               "B02, B03). The web service alone can be rolled back by hand "
                               "with the previous unit the installer kept; see "
                               "control/web/README.md."},
                ],
            },
        }

    def status(self, deadline=None):
        deadline = time.monotonic() + REQUEST_TIMEOUT if deadline is None else deadline
        with self.acquired(deadline):
            now = time.monotonic()
            if self.cached and now - self.cache_time < 2:
                # Audio is not cached: another controller may have changed it.
                return dict(self.cached, audio=self.audio(deadline))
            data, previous = metrics(self.root, self.previous,
                                     now - self.sample_time if self.sample_time else None)
            data.update(hostname=socket.gethostname(), architecture=platform.machine(),
                        os=platform.system() + " " + platform.release(),
                        selected_hardware=self.metadata, power=self.power(deadline),
                        components=self.components(deadline), audio=self.audio(deadline))
            self.previous, self.sample_time, self.cached = previous, now, data
            self.cache_time = time.monotonic()
            return data


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 8
    request_timeout = REQUEST_TIMEOUT

    def __init__(self, address, backend, token, hosts, devices=None, discovery=None):
        # token None is the explicit development bypass (`--auth none`). It is a
        # mode, not a missing key: every request then carries no authentication.
        if token is not None and not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
            raise ValueError("Access key must be 32–128 URL-safe characters")
        self.backend, self.token = backend, token
        self.auth_mode = "none" if token is None else "key"
        self.devices = tuple(devices or ())
        self.discovery = discovery
        self.hosts = frozenset(hosts)
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(address, Handler)

    def server_close(self):
        if self.discovery is not None:
            self.discovery.stop.set()
        super().server_close()

    def verify_request(self, request, client_address):
        request.settimeout(5)
        return self.slots.acquire(blocking=False)

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "Debra"

    def handle(self):
        self.deadline = time.monotonic() + self.server.request_timeout
        # A socket inactivity timeout alone permits slow-drip headers/body.
        # Shutdown also interrupts a buffered read when bytes keep arriving.
        timer = threading.Timer(self.server.request_timeout, self.expire)
        timer.daemon = True
        timer.start()
        try:
            super().handle()
        except (ConnectionError, TimeoutError):
            pass
        finally:
            timer.cancel()

    def expire(self):
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def log_message(self, *args):
        # Never log Authorization, fragments accidentally sent as queries, or data.
        pass

    def reply(self, code, data, mime="application/json"):
        body = json.dumps(data, allow_nan=False).encode() if mime == "application/json" else data
        self.send_response(code)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; "
                         "script-src 'self'; style-src 'self'; connect-src 'self'; "
                         "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def safe_navigation(self):
        """Whether this is a browser following a link to this page.

        A Switch link goes from another Debra's page to this one, so the browser
        marks the request `cross-site`. That is an ordinary top-level navigation
        to a public page, and refusing it showed the person a JSON error instead
        of the device. Only a GET for a static asset, with the Fetch Metadata of
        a real navigation, qualifies: no key, no query, and the same bytes are
        served to anyone who types the address. Everything else stays refused.
        """
        return (self.command == "GET"
                and self.path in STATIC
                and self.headers.get("Sec-Fetch-Mode") == "navigate"
                and self.headers.get("Sec-Fetch-Dest") == "document")

    def permitted(self, write=False):
        host = self.headers.get("Host", "")
        if len(self.headers.get_all("Host", [])) != 1 or host not in self.server.hosts:
            self.reply(403, {"error": "Unrecognized host"})
            return False
        if (self.headers.get("Sec-Fetch-Site") == "cross-site"
                and not self.safe_navigation()):
            self.reply(403, {"error": "Cross-site request refused"})
            return False
        origin = self.headers.get("Origin")
        if (len(self.headers.get_all("Origin", [])) > 1 or
                (origin is not None or write) and origin != "http://" + host):
            self.reply(403, {"error": "Same-origin request required"})
            return False
        if self.path.startswith("/api/") and self.path != "/api/devices":
            # /api/devices is the pre-pairing "one-stop" link list: hostnames
            # only, no device state, so it must work before a key is entered.
            if self.server.token is not None:
                auth = self.headers.get("Authorization", "")
                if (len(self.headers.get_all("Authorization", [])) != 1 or
                        not hmac.compare_digest(auth.encode(), ("Bearer " + self.server.token).encode())):
                    self.reply(401, {"error": "Access key required"})
                    return False
        return True

    def do_GET(self):
        if not self.permitted():
            return
        if self.path in STATIC:
            name, mime = STATIC[self.path]
            self.reply(200, (ASSETS / name).read_bytes(), mime)
        elif self.path == "/api/devices":
            try:
                discovered = self.server.discovery.snapshot() if self.server.discovery else ()
                status = self.server.discovery.status() if self.server.discovery else {
                    "enabled": False, "found": 0, "seconds_since_scan": None, "error": None}
            except Exception:
                discovered, status = (), {"enabled": False, "found": 0,
                                          "seconds_since_scan": None, "error": "discovery unavailable"}
            # `self` lets the page mark its own row instead of offering to switch
            # to itself. It is the serving host's name and port, nothing else.
            self.reply(200, {"devices": merge_devices(self.server.devices, discovered),
                             "self": {"hostname": socket.gethostname(),
                                      "port": self.server.server_address[1]},
                             "discovery": status})
        elif self.path == "/api/status":
            try:
                data = self.server.backend.status(deadline=self.deadline)
                data["auth"] = self.server.auth_mode
                self.reply(200, data)
            except (Unavailable, RequestExpired):
                self.reply(503, {"error": "Status unavailable; request timed out"})
        elif self.path == "/api/setup":
            # Read-only: every build choice is reported with a reason it cannot
            # be changed, so there is no matching POST path to accept one.
            try:
                self.reply(200, self.server.backend.setup(deadline=self.deadline))
            except (Unavailable, RequestExpired):
                self.reply(503, {"error": "Setup state unavailable; request timed out"})
        else:
            self.reply(404, {"error": "Not found"})

    def do_POST(self):
        if not self.permitted(write=True):
            return
        if self.path not in ("/api/audio/volume", "/api/audio/mute"):
            self.reply(404, {"error": "Not found"})
            return
        try:
            lengths = self.headers.get_all("Content-Length", [])
            if (len(lengths) != 1 or self.headers.get_all("Transfer-Encoding") is not None or
                    not re.fullmatch(r"[0-9]+", lengths[0])):
                raise ValueError("One Content-Length required; chunked requests unsupported")
            length = int(lengths[0])
            if not 0 < length <= 1024:
                raise ValueError("Request must be 1–1024 bytes")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Use application/json")
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError("Incomplete request")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
            result = self.server.backend.change_audio(
                self.path.rsplit("/", 1)[1], payload, deadline=self.deadline)
            self.reply(200, result)
        except (ValueError, UnicodeError):
            self.reply(400, {"error": "Invalid audio request"})
        except (Unavailable, RequestExpired):
            self.reply(503, {"error": "Audio control unavailable; no fallback or restart attempted"})


def init_state(state):
    """Create private state without replacing or rotating an existing key."""
    state.mkdir(parents=True, mode=0o700, exist_ok=True)
    if state.is_symlink() or state.stat().st_uid != os.getuid() or stat.S_IMODE(state.stat().st_mode) & 0o077:
        raise ValueError("State directory must be owned by this user and owner-only (0700)")
    token_path = state / "access.key"
    if token_path.exists() or token_path.is_symlink():
        load_key(state)
        return False
    # Never expose an empty/truncated final key. Retain private staging
    # artifacts (even after success) rather than discard interrupted evidence.
    fd, staged = tempfile.mkstemp(prefix=".access-key.staged-", dir=state)
    with os.fdopen(fd, "w") as stream:
        stream.write(secrets.token_urlsafe(32) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        # Hard-link publication is atomic and cannot replace a competing key.
        os.link(staged, token_path)
    except FileExistsError:
        load_key(state)
        return False
    return True


def load_key(state):
    if state.is_symlink() or state.stat().st_uid != os.getuid() or stat.S_IMODE(state.stat().st_mode) & 0o077:
        raise ValueError("State directory must be owned by this user and owner-only (0700)")
    fd = os.open(state / "access.key", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "r") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
                stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > 129):
            raise ValueError("Access key must be an owner-only regular file (0600)")
        token = stream.read().strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,128}", token):
        raise ValueError("Invalid access key; existing file was not replaced")
    return token


def valid_hosts(hosts):
    return bool(hosts) and all(re.fullmatch(r"[a-zA-Z0-9.-]+:\d+", h) and
                               urlsplit("http://" + h).netloc == h for h in hosts)


def canonical_device_url(url):
    return discovery.canonical_device_url(url)


def validate_device(item):
    return discovery.validate_device(item)


def validate_listening_port(port):
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("--port must be an integer from 1024 to 65535 (an unprivileged port)")


def load_devices(path):
    """Read the optional one-stop device list.

    Only plain http host:port links are accepted, so this file can never point a
    browser at a credential-bearing or non-web URL. It is read once at startup.
    """
    data = json.loads(Path(path).read_text())
    if not isinstance(data, list):
        raise ValueError("Device list must be a JSON array")
    if len(data) > 50:
        raise ValueError("Device list allows at most 50 entries")
    return [validate_device(item) for item in data]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "serve"])
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".config/debra/web")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--host", action="append", default=[],
                        help="Allowed browser authority, including :port; repeatable")
    parser.add_argument("--sink", help="Explicit pactl sink name; never follows hotplug")
    parser.add_argument("--auth", choices=["key", "none"], default="key",
                        help="key: require the device access key (default); "
                             "none: development bypass, no authentication at all")
    parser.add_argument("--devices", type=Path,
                        help="JSON list of known devices for the one-stop card")
    args = parser.parse_args()
    state = args.state_dir
    if args.action == "init":
        try:
            created = init_state(state)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print("Access key created" if created else "Existing access key preserved")
        return
    try:
        validate_listening_port(args.port)
    except ValueError as exc:
        parser.error(str(exc))
    if not args.sink:
        parser.error("--sink is required")
    hosts = args.host or (["127.0.0.1:" + str(args.port)] if args.bind == "127.0.0.1" else [])
    if not valid_hosts(hosts):
        parser.error("Supply explicit --host hostname:port values for LAN binding")
    devices = []
    if args.devices:
        try:
            devices = load_devices(args.devices)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    token = None
    if args.auth == "key":
        try:
            token = load_key(state)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    elif args.bind != "127.0.0.1":
        print("WARNING: --auth none exposes unauthenticated control on " + args.bind, flush=True)
    metadata_path = state / "hardware.json"
    metadata = {}
    if metadata_path.exists():
        # A malformed file must not traceback: the unit is Restart=on-failure, so
        # an unhandled error becomes a silent restart loop with no usable reason.
        try:
            metadata = json.loads(metadata_path.read_text())
        except (OSError, ValueError) as exc:
            parser.error(f"hardware.json is not readable JSON ({exc}); fix or remove it")
        if (not isinstance(metadata, dict) or set(metadata) - {"hat", "speaker"} or
                any(not isinstance(v, str) or len(v) > 160 for v in metadata.values())):
            parser.error("hardware.json allows only hat/speaker labels up to 160 characters")
    backend = Backend(args.sink, metadata)
    discovery = DiscoveryCache()
    with Server((args.bind, args.port), backend, token, hosts, devices, discovery) as server:
        discovery.start()
        print("Debra web prototype listening; no audio settings changed", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
