#!/bin/sh
# OPTIONAL LAB EXTRA — NOT PART OF DEBRA, AND NOT A DEVICE-BUILD STEP.
#
# A Debra device is a voice/music client: Home Assistant and Music Assistant
# stay on the household server. This script exists only to give a lab Sendspin
# player an isolated Music Assistant *source* to test against, so a test never
# plays through the household instance or its speakers.
#
# Do not install it on a Debra device. Do not install it because the file is in
# this directory. The numeric prefix is historical (it was recorded as step 40 of
# the 2026-11-15 lab bring-up); it is not a build order.
#
# The container is not enabled at boot: 51-power-cap.sh disables
# docker.service and docker.socket, so an installed Docker does not start again
# after a reboot. Nothing in Debra depends on it.
#
# Docker with host networking is the only supported non-HAOS install: MA
# discovers and streams to players over mDNS and random TCP/UDP ports.
# First run: http://<host>:8095/setup creates the admin account. There is no
# passwordless path, and the credentials must stay out of Git.
#
# Usage: MA_VERSION=2.10.12 40-music-assistant.sh
set -eu
VERSION="${MA_VERSION:-2.10.12}"

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io
sudo usermod -aG docker "$USER"

sudo install -d -m 0755 "$HOME/ma-data"
sudo docker rm -f music-assistant 2>/dev/null || true
sudo docker run -d \
  --name music-assistant \
  --restart unless-stopped \
  --network host \
  -v "$HOME/ma-data:/data" \
  -e LOG_LEVEL=info \
  "ghcr.io/music-assistant/server:$VERSION"

sleep 10
sudo docker ps --filter name=music-assistant --format '{{.Names}} {{.Image}} {{.Status}}'
ss -ltn 2>/dev/null | grep -E ':(8095|8097)' || echo 'MA ports not listening yet'
