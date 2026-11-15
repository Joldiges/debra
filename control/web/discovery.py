"""Browse and parse Debra mDNS announcements using avahi-browse."""

from __future__ import annotations

import re
import subprocess

SERVICE = "_debra._tcp"
BROWSE_TIMEOUT_S = 8
# A record we are willing to hand to the browser: a plain HTTP link with no
# path, query or fragment, exactly like the configured list.
URL = re.compile(r"^http://[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251})\.local(?::(\d{1,5}))?/$")


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


def parse(output: str) -> list[dict]:
    """Turn ``avahi-browse -rtp`` output into one record per service."""
    found: dict[tuple[str, int], dict] = {}
    for line in output.splitlines():
        if not line.startswith("="):
            continue
        fields = _split(line)
        if len(fields) < 10:
            continue
        _, _iface, protocol, instance, service, _domain, host, address, port, txt = fields[:10]
        if protocol not in ("IPv4", "IPv6") or service != SERVICE:
            continue
        if not port.isdigit() or not 1 <= int(port) <= 65535:
            continue
        if not host.endswith(".local"):
            continue
        key = (instance, int(port))
        record = found.get(key)
        if record is None:
            attributes = _txt(txt)
            record = {
                "name": attributes.get("name") or instance,
                "label": attributes.get("label") or instance,
                "url": f"http://{host}:{int(port)}/",
                "host": host,
                "addresses": [],
            }
            found[key] = record
        if address and address not in record["addresses"]:
            record["addresses"].append(address)
    records = [record for record in found.values() if URL.match(record["url"])]
    records.sort(key=lambda record: record["name"])
    return records


def browse(timeout: float = BROWSE_TIMEOUT_S) -> dict:
    """Browse for Debra devices. Returns ``{"devices": [...], "error": None|str}``."""
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
    return {"devices": parse(proc.stdout), "error": None}
