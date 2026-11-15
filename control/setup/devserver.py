"""Run the setup page locally against a fake NetworkManager.

This is how the onboarding journey is exercised without a Pi: it serves the real
page and the real state machine, so what you click is what a device would serve.
Nothing here touches a radio, root or the network.

    python3 -B control/setup/devserver.py --port 8099
    python3 -B control/setup/devserver.py --phase failed --error "Wrong password"
    python3 -B control/setup/devserver.py --behaviour bad-psk

Then open http://127.0.0.1:8099/ . Submitting the form runs the real transition:
the page answers, the fake access point drops, the fake join happens, and the
page comes back as online or failed.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import onboarding  # noqa: E402
import state as state_module  # noqa: E402
from fake_nm import FakeNetwork  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8099)
    parser.add_argument("--phase", choices=state_module.PHASES, default="hotspot",
                        help="starting phase, so a state can be inspected directly")
    parser.add_argument("--error", default="", help="last_error to show in the failed state")
    parser.add_argument("--baseline-error", default="",
                        help="baseline_error to show in the online state")
    parser.add_argument("--ssid", default="HomeWiFi", help="SSID to show when online")
    parser.add_argument("--country", default=None, help="preset country, e.g. GB")
    parser.add_argument("--behaviour", default="ok",
                        choices=["ok", "bad-psk", "no-address", "no-uplink",
                                 "scan-fails"])
    parser.add_argument("--state-dir", type=Path, default=None,
                        help="keep the state instead of using a temporary directory")
    args = parser.parse_args()

    directory = args.state_dir or Path(tempfile.mkdtemp(prefix="debra-setup-", dir="/tmp/opencode"))
    state_path = directory / "setup.json"
    data = state_module.blank("debra-demo1")
    data["phase"] = args.phase
    data["country"] = args.country
    data["last_error"] = args.error or None
    data["ssid"] = args.ssid if args.phase == "online" else None
    data["address"] = "192.0.2.40" if args.phase == "online" else None
    # A device with a failed baseline has no baseline: the two are exclusive, so
    # the fixture cannot show a success and a failure at the same time.
    online = args.phase == "online"
    data["baseline"] = (str(directory / "baseline")
                        if online and not args.baseline_error else None)
    data["baseline_error"] = (args.baseline_error or None) if online else None
    if args.phase == "hotspot":
        data["hotspot"] = {"ssid": "Debra-Setup-demo1", "interface": "wlan0"}
    state_module.write(state_path, data)

    network = FakeNetwork(country=args.country, behaviour=args.behaviour)
    # A fake root, so the success path cannot copy the real NetworkManager
    # keyfiles of whatever machine this is running on.
    fake_root = directory / "fake-root"
    keyfiles = directory / "keyfiles"
    for path in (fake_root, keyfiles):
        path.mkdir(parents=True, exist_ok=True)
    onboarder = onboarding.Onboarder(
        network, state_path, directory / "baseline", root=fake_root,
        card_note_path=directory / "debra-setup.txt", keyfile_dir=keyfiles)
    if data["hotspot"]:
        # The state was preset rather than reached through start_hotspot(), so
        # do what a boot does before it raises the access point: look around
        # while the radio is still free.
        onboarder.refresh_networks(data["hotspot"]["interface"])
    server = onboarding.Portal(("127.0.0.1", args.port), onboarder,
                               HERE / "assets" / "setup.html")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"setup page: http://127.0.0.1:{args.port}/  (state in {directory})", flush=True)
    print(f"card note:  {directory / 'debra-setup.txt'}  "
          f"(the setup-network password a person needs)", flush=True)
    try:
        thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
