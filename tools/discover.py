"""Find Debra devices on the local network, over mDNS.

    python tools/discover.py            # one scan, prints a table
    python tools/discover.py --json     # one scan, prints the device list

A Debra device publishes ``_debra._tcp`` when its advertisement is running
(``avahi-publish-service``, or the ``debra-advertise`` user unit). This tool
browses for that service with ``avahi-browse`` and returns the same record shape
the browser page already understands: ``name``, ``url`` and ``label``.

It reads; it does not write, connect to the advertised HTTP port, or change any
service. A missing ``avahi-browse``, a stopped daemon or a timeout all return an
empty list with a reason, never an exception, because discovery is a
convenience and the configured list must keep working without it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Direct script execution puts tools/, not the repository root, on sys.path.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from control.web import discovery  # noqa: E402


def device_list() -> list[dict]:
    """The discovery result in the shape the browser's device list uses."""
    return [{"name": record["name"], "url": record["url"], "label": record["label"]}
            for record in discovery.browse()["devices"]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print the device list as JSON")
    args = parser.parse_args(argv)
    result = discovery.browse()
    if args.json:
        print(json.dumps(result, indent=1))
        return 0
    if result["error"]:
        print(f"Discovery unavailable: {result['error']}")
        return 1
    if not result["devices"]:
        print(f"No {discovery.SERVICE} service found. Is the device advertising?")
        return 0
    print(f"{'Name':22s} {'Label':28s} {'URL':34s} Address")
    for record in result["devices"]:
        print(f"{record['name']:22s} {record['label'][:28]:28s} {record['url']:34s} "
              + ", ".join(record["addresses"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
