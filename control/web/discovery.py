"""Publish, browse and parse Debra mDNS announcements."""

from __future__ import annotations

import ipaddress
import logging
import re
import subprocess
import threading
import time

SERVICE = "_debra._tcp"
BROWSE_TIMEOUT_S = 8
LOGGER = logging.getLogger(__name__)


def canonical_device_url(url):
    # Restrict the grammar before parsing: URL parsers otherwise discard some
    # whitespace and normalize numeric hostnames differently across platforms.
    if not isinstance(url, str) or len(url) > 200:
        raise ValueError("URL must be a string up to 200 characters")
    match = re.fullmatch(r"(?i:http)://([A-Za-z0-9.-]+):([0-9]{1,5})/?", url, re.ASCII)
    if not match:
        raise ValueError("Expected http://host:port/ without a path, query or fragment")
    host, port_text = match.groups()
    host, port = host.lower(), int(port_text)
    labels = host.split(".")
    if (len(host) > 253 or not 1 <= port <= 65535 or
            any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in labels)):
        raise ValueError("Invalid host or port")
    if port == 80:
        # Browsers drop a default port, so the anchor would become http://host/
        # and the Host check would then reject the page it just linked to.
        raise ValueError("Port 80 is unsupported: browsers drop the default port, "
                         "so the link would not match this service's Host check")
    if labels[-1].isdigit() or re.fullmatch(r"0x[0-9a-f]*", labels[-1]):
        try:
            if str(ipaddress.IPv4Address(host)) != host:
                raise ValueError("Noncanonical IPv4 address")
        except ipaddress.AddressValueError as exc:
            raise ValueError("Invalid IPv4 address") from exc
    canonical = f"http://{host}:{port}/"
    if len(canonical) > 200:
        raise ValueError("Canonical URL exceeds 200 characters")
    return canonical


def validate_device(item):
    """Validate configured links; discovery adds a .local-only restriction."""
    if not isinstance(item, dict) or set(item) - {"name", "url", "label"}:
        raise ValueError("Each device allows only name, url and label")
    name, url, label = item.get("name"), item.get("url"), item.get("label", "")
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", name):
        raise ValueError("Device name must be 1-64 letters, digits, dot, dash or underscore")
    if not isinstance(url, str) or len(url) > 200:
        raise ValueError(f"Device {name}: url must be a string up to 200 characters")
    try:
        url = canonical_device_url(url)
    except ValueError as exc:
        raise ValueError(f"Device {name}: invalid URL: {exc}") from exc
    if not isinstance(label, str) or len(label) > 80:
        raise ValueError(f"Device {name}: label must be a string up to 80 characters")
    return {"name": name, "url": url, "label": label}


def accept_record(record):
    """Return (canonical browser entry, None), or (None, rejection reason).

    Both the CLI parser and hub use this contract. Auxiliary discovery fields
    (host and addresses) are not browser links and are not copied to the entry.
    """
    if not isinstance(record, dict):
        return None, "Discovery record must be an object"
    try:
        item = validate_device({"name": record["name"], "url": record["url"],
                                "label": record.get("label", "")})
    except KeyError as exc:
        return None, f"Discovery record is missing {exc.args[0]}"
    except ValueError as exc:
        return None, str(exc)
    host = item["url"].split("/", 3)[2].rsplit(":", 1)[0]
    if not host.endswith(".local"):
        return None, "Discovered host must end with .local"
    return item, None


def _unescape(field: str) -> str:
    """Decode avahi-browse's escapes.

    avahi-browse -t writes an escaped field as ``\\DDD`` with **three decimal**
    digits — a space is ``\\032`` — and ``\\\\`` for a literal backslash. Taking
    the backslash away and keeping the digits turned every unlabelled device's
    name into ``Debra032debra-8518d6`` in another device's list, which is the one
    place a person reads that name.
    """
    out, index = [], 0
    while index < len(field):
        char = field[index]
        if char == "\\" and index + 1 < len(field):
            digits = field[index + 1:index + 4]
            if len(digits) == 3 and digits.isdigit() and int(digits) < 256:
                out.append(chr(int(digits)))
                index += 4
                continue
            # Any other escaped character stands for itself: \; -> ;, \\ -> \.
            out.append(field[index + 1])
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _split(line: str) -> list[str]:
    """Split an avahi-browse -p line on unescaped semicolons.

    Escapes are kept intact: an escaped semicolon is not a separator, and the
    decoder needs the digits avahi wrote. `_unescape` is applied to the fields
    actually used as text.
    """
    fields, current, index = [], [], 0
    while index < len(line):
        char = line[index]
        if char == "\\" and index + 1 < len(line):
            width = 4 if (index + 4 <= len(line) and line[index + 1:index + 4].isdigit()) else 2
            current.append(line[index:index + width])
            index += width
            continue
        if char == ";":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
        index += 1
    fields.append("".join(current))
    return fields


def _txt(field: str) -> dict[str, str]:
    """Parse avahi's space-separated quoted TXT pairs, then decode each one.

    Pairs are matched on the still-escaped text, so a value containing a quote
    (avahi writes ``\\034``) cannot end the pair early, and the escape is decoded
    afterwards.
    """
    pairs = {}
    for item in re.findall(r'"([^"]*)"', field):
        key, _, value = item.partition("=")
        key = _unescape(key)
        if key:
            pairs[key] = _unescape(value)
    return pairs


def parse(output: str, refused: list | None = None) -> list[dict]:
    """Turn ``avahi-browse -rtp`` output into one record per service.

    A record this function refuses is dropped from the result, so `refused`
    collects why. Without it the hub could only report refusals it made itself
    and the parser's were invisible to the page: the reader saw a successful
    empty scan where an advertisement had been rejected.
    """
    found: dict[tuple[str, int], dict] = {}
    for line in output.splitlines():
        if not line.startswith("="):
            continue
        fields = _split(line)
        if len(fields) < 10:
            LOGGER.warning("Dropped discovery record: malformed resolved avahi line")
            if refused is not None:
                refused.append({"name": "unparseable", "reason": "malformed resolved avahi line"})
            continue
        _, _iface, protocol, instance, service, _domain, host, address, port, txt = fields[:10]
        if protocol not in ("IPv4", "IPv6") or service != SERVICE:
            continue
        # avahi escapes a space as \032; undecoded, an unlabelled device showed
        # up in another device's list as "Debra032debra-8518d6".
        instance = _unescape(instance)
        attributes = _txt(txt)
        item, reason = accept_record({
            "name": attributes.get("name") or instance,
            "label": attributes.get("label") or instance,
            "url": f"http://{host}:{port}/",
        })
        if reason is not None:
            # CLI stdout stays machine-readable in --json mode. The same
            # diagnostic reaches the service's stderr/journal on hub scans.
            LOGGER.warning("Dropped discovery record %r: %s", instance, reason)
            if refused is not None:
                refused.append({"name": str(instance), "reason": reason})
            continue
        authority = item["url"].split("/", 3)[2]
        canonical_host, canonical_port = authority.rsplit(":", 1)
        key = (instance, int(canonical_port))
        record = found.get(key)
        if record is None:
            record = {
                **item,
                "host": canonical_host,
                "addresses": [],
            }
            found[key] = record
        if address and address not in record["addresses"]:
            record["addresses"].append(address)
    records = list(found.values())
    records.sort(key=lambda record: record["name"])
    return records


def browse(timeout: float = BROWSE_TIMEOUT_S) -> dict:
    """Browse for Debra devices.

    Returns ``{"devices": [...], "refused": [...], "error": None|str}``. `refused`
    names each advertisement this parser dropped and why, so a hub can show the
    refusal instead of an empty but successful scan.
    """
    try:
        proc = subprocess.run(
            ["avahi-browse", "-rtp", "-t", SERVICE],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except FileNotFoundError:
        return {"devices": [], "error": "avahi-browse is not installed"}
    except subprocess.TimeoutExpired:
        return {"devices": [], "error": "avahi-browse timed out"}
    except OSError as exc:
        return {"devices": [], "error": f"avahi-browse unavailable ({exc.__class__.__name__})"}
    if proc.returncode != 0:
        return {"devices": [], "error": f"avahi-browse exited {proc.returncode}"}
    refused: list[dict] = []
    devices = parse(proc.stdout, refused)
    return {"devices": devices, "refused": refused, "error": None}


ANNOUNCE_RESTART_S = 5


def service_name(hostname: str) -> str:
    """The mDNS instance name this project publishes under."""
    return f"Debra {hostname}"


def _read_last_line(stream, tail: list) -> None:
    """Keep the last thing the publisher said, without ever blocking a caller."""
    try:
        for line in stream:
            text = (line.decode("utf-8", "replace") if isinstance(line, bytes)
                    else str(line)).strip()
            if text:
                tail[:] = [text[:200]]
    except (OSError, ValueError):
        pass
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            pass


def _terminate(process) -> None:
    for method in ("terminate", "kill"):
        try:
            getattr(process, method)()
            process.wait(timeout=2)
            return
        except (OSError, AttributeError, TypeError):
            continue
        except subprocess.TimeoutExpired:
            continue


class Announcer:
    """This device's own ``_debra._tcp`` advertisement, published by the server.

    **Why the server publishes it and not a unit of its own.** A hand-written
    ``debra-advertise`` user unit was how this started, on the lab Pi 5 only, and
    that is exactly why discovery looked broken: every other device browsed this
    network, found one advertisement, and truthfully reported one device. The
    service that owns the port is the only thing that knows the port, so it
    publishes the record itself and the record cannot disagree with reality.

    Nothing here needs root: ``avahi-publish-service`` is an ordinary user
    program. It is spawned as a child of this process and dies with it, so a
    stopped server stops being advertised instead of leaving a record pointing at
    a port nothing answers.

    Failure is reported, never hidden. A missing publisher, or a publisher that
    exits, becomes a reason the page shows; it does not become a device that
    quietly stops being discoverable.
    """

    def __init__(self, hostname, port, label="", *, spawn=None, enabled=True,
                 disabled_reason=None, restart_delay=ANNOUNCE_RESTART_S):
        self.hostname, self.port, self.label = hostname, port, label or ""
        self.enabled = bool(enabled)
        self.disabled_reason = disabled_reason
        self.restart_delay = restart_delay
        self.spawn = spawn or self._spawn
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.process = None
        self.started_at = None
        self.spawns = 0
        self.last_error = None
        self.thread = None

    def argv(self):
        argv = ["avahi-publish-service", "--no-fail", service_name(self.hostname),
                SERVICE, str(self.port), f"name={self.hostname}"]
        if self.label:
            argv.append(f"label={self.label}")
        return argv

    @staticmethod
    def _spawn(argv):
        return subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def _fail(self, message, disable):
        with self.lock:
            self.last_error = message
            if disable:
                self.enabled = False

    def _supervise(self):
        while not self.stop_event.is_set():
            try:
                process = self.spawn(self.argv())
            except FileNotFoundError:
                self._fail("avahi-publish-service is not installed", disable=True)
                return
            except OSError as exc:
                self._fail(f"avahi-publish-service could not start ({type(exc).__name__})",
                           disable=True)
                return
            tail = []
            reader = None
            stream = getattr(process, "stdout", None)
            if stream is not None:
                reader = threading.Thread(target=_read_last_line, args=(stream, tail),
                                          daemon=True, name="debra-announce-log")
                reader.start()
            with self.lock:
                self.process, self.spawns = process, self.spawns + 1
                self.started_at = time.monotonic()
                self.last_error = None
            while not self.stop_event.is_set() and process.poll() is None:
                self.stop_event.wait(0.5)
            stopping = self.stop_event.is_set()
            if stopping:
                _terminate(process)
            if reader is not None:
                reader.join(timeout=1)
            with self.lock:
                self.process = None
            if stopping:
                return
            # It exited by itself. Say so, keep trying, and let the page show the
            # reason rather than leaving this device invisible with no clue.
            code = getattr(process, "returncode", None)
            self._fail("the advertisement stopped"
                       + ("" if code is None else f" (exit code {code})")
                       + (f": {tail[0]}" if tail else ""), disable=False)
            self.stop_event.wait(self.restart_delay)

    def start(self):
        if not self.enabled:
            return False
        self.thread = threading.Thread(target=self._supervise, daemon=True,
                                       name="debra-announce")
        self.thread.start()
        return True

    def stop(self):
        self.stop_event.set()

    def running(self):
        with self.lock:
            return self.enabled and self.process is not None and self.process.poll() is None

    def status(self):
        """Whether this device is announcing itself, and what went wrong if not."""
        with self.lock:
            process = self.process
            alive = (self.enabled and process is not None and process.poll() is None)
            age = (round(max(0.0, time.monotonic() - self.started_at))
                   if alive and self.started_at is not None else None)
            return {"enabled": self.enabled, "running": alive,
                    "instance": service_name(self.hostname), "port": self.port,
                    "label": self.label or None, "spawns": self.spawns,
                    "seconds_running": age, "error": self.last_error,
                    "reason": self.disabled_reason}
