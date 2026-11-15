"""First-boot setup: identity, Wi-Fi onboarding and the first baseline.

Runs on a device as root, and on a laptop against `fake_nm.FakeNetwork`. The
split is deliberate: every decision lives in these modules, and the only thing
that needs real hardware is the thin `nm.Nmcli` adapter behind them.
"""
