#!/usr/bin/env python3
import argparse
import hashlib
from pathlib import Path

def read_first_existing(paths: list[str]) -> str | None:
    for p in paths:
        try:
            data = Path(p).read_text(errors="ignore").strip()
            if data:
                return data
        except Exception:
            continue
    return None

def get_platform_id() -> str:
    serial = read_first_existing(["/sys/firmware/devicetree/base/serial-number"])
    if serial:
        return f"rpi:{serial}"

    cpuinfo = read_first_existing(["/proc/cpuinfo"])
    if cpuinfo:
        for line in cpuinfo.splitlines():
            if line.lower().startswith("serial"):
                _, v = line.split(":", 1)
                v = v.strip()
                if v:
                    return f"cpu:{v}"

    dmi = read_first_existing(["/sys/class/dmi/id/product_uuid"])
    if dmi:
        return f"dmi:{dmi}"

    mid = read_first_existing(["/etc/machine-id"])
    if mid:
        return f"mid:{mid}"

    try:
        for p in Path("/sys/class/net").glob("*/address"):
            mac = p.read_text().strip()
            if mac and mac != "00:00:00:00:00:00":
                return f"mac:{mac}"
    except Exception:
        pass

    return "unknown"

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--short", type=int, default=6, help="Number of hex chars to output")
    args = ap.parse_args()

    raw = get_platform_id().encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    print(digest[: args.short])

if __name__ == "__main__":
    main()
