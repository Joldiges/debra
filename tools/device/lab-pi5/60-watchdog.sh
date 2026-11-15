#!/bin/sh
# Watchdog layers for the lab Pi.
#
# What this device actually did on 2026-11-15: ping answered, TCP port 22
# accepted, and sshd never sent a banner for five minutes. The kernel was fine
# and PID 1 was healthy, so systemd kept petting the hardware watchdog and
# nothing reset the board. The failure was a process stuck in uninterruptible
# sleep, most likely on the SD card.
#
# Three layers, because they catch different things:
#   1. hardware watchdog (systemd, 60 s) - catches a dead or wedged kernel/PID 1
#   2. hung_task_panic (kernel, 120 s)   - catches one process stuck in D state
#   3. debra-health timer (61-health.sh) - catches "running but silent"
#
# Plus a persistent journal, because a hang that leaves no log is not diagnosable.
set -eu

# --- 1. persistent journal, capped -------------------------------------------
# Raspberry Pi OS ships Storage=volatile (40-rpi-volatile-storage.conf) so the
# SD card is spared. That is right for a finished appliance and wrong for a
# device being diagnosed, and the drop-in has to be masked: a later drop-in
# alone did not override it here.
sudo mkdir -p /etc/systemd/journald.conf.d /var/log/journal
sudo ln -sf /dev/null /etc/systemd/journald.conf.d/40-rpi-volatile-storage.conf
sudo tee /etc/systemd/journald.conf.d/50-debra-persistent.conf >/dev/null <<'EOF'
[Journal]
Storage=persistent
SystemMaxUse=64M
SystemMaxFileSize=8M
EOF

# --- 2. kernel: a stuck task becomes a reboot --------------------------------
sudo tee /etc/sysctl.d/60-debra-watchdog.conf >/dev/null <<'EOF'
# A task in uninterruptible sleep for two minutes is not going to recover.
# Panic, then let kernel.panic reboot after ten seconds.
kernel.hung_task_timeout_secs = 120
kernel.hung_task_panic = 1
kernel.panic = 10
EOF

# --- 3. make the hardware watchdog explicit ----------------------------------
sudo mkdir -p /etc/systemd/system.conf.d
sudo tee /etc/systemd/system.conf.d/50-debra-watchdog.conf >/dev/null <<'EOF'
[Manager]
RuntimeWatchdogSec=60s
RebootWatchdogSec=5min
EOF

sudo sysctl --system >/dev/null
sudo systemctl restart systemd-journald
sudo systemctl daemon-reexec
sleep 2

echo "--- kernel:"
sysctl kernel.hung_task_panic kernel.hung_task_timeout_secs kernel.panic
echo "--- hardware watchdog:"
busctl get-property org.freedesktop.systemd1 /org/freedesktop/systemd1 \
  org.freedesktop.systemd1.Manager RuntimeWatchdogUSec
echo "--- journal:"
journalctl --header | grep -m1 "File path"
