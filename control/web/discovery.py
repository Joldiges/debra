"""Browse and parse Debra mDNS announcements using avahi-browse."""

from __future__ import annotations

import ipaddress
import logging
import re
import subprocess

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


def _split(line: str) -> list[str]:
    """Split an avahi-browse -p line on unescaped semicolons."""
    fields, current, escaped = [], [], False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ";":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    fields.append("".join(current))
    return fields


def _txt(field: str) -> dict[str, str]:
    """Parse avahi's space-separated quoted TXT pairs."""
    pairs = {}
    for item in re.findall(r'"([^"]*)"', field):
        key, _, value = item.partition("=")
        if key:
            pairs[key] = value
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
