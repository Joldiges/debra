# syntax=docker/dockerfile:1.7
ARG SUITE=trixie
ARG MIRROR=http://raspbian.raspberrypi.org/raspbian

FROM --platform=$BUILDPLATFORM debian:trixie-slim AS rootfs
ENV QEMU_CPU=arm1176
ARG SUITE
ARG MIRROR


SHELL ["/bin/bash", "-euxo", "pipefail", "-c"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    debootstrap qemu-user-static ca-certificates wget gnupg xz-utils \
  && rm -rf /var/lib/apt/lists/*

# Raspbian archive key
RUN mkdir -p /usr/share/keyrings \
 && wget -qO- https://archive.raspbian.org/raspbian.public.key \
    | gpg --dearmor -o /usr/share/keyrings/raspbian-archive-keyring.gpg

# Bootstrap Raspbian (armhf) rootfs
RUN debootstrap --arch=armhf --variant=minbase --foreign \
    --no-check-gpg \
    "${SUITE}" /rootfs "${MIRROR}"

# Enable running ARM binaries in chroot
RUN cp /usr/bin/qemu-arm-static /rootfs/usr/bin/ \
 && chroot /rootfs /debootstrap/debootstrap --second-stage

# Apt sources inside rootfs
RUN mkdir -p /rootfs/usr/share/keyrings \
 && cp /usr/share/keyrings/raspbian-archive-keyring.gpg /rootfs/usr/share/keyrings/raspbian-archive-keyring.gpg \
 && cat > /rootfs/etc/apt/sources.list.d/raspbian.sources <<EOF
Types: deb
URIs: ${MIRROR}
Suites: ${SUITE}
Components: main contrib non-free non-free-firmware rpi
Signed-By: /usr/share/keyrings/raspbian-archive-keyring.gpg
EOF

# Minimal toolchain for building painful wheels
RUN chroot /rootfs bash -lc "apt-get update && \
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates \
    python3 python3-pip python3-venv python3-dev \
    build-essential pkg-config git curl \
    libssl-dev libffi-dev \
    cargo rustc \
  && rm -rf /var/lib/apt/lists/*"

FROM scratch
COPY --from=rootfs /rootfs/ /

ENV QEMU_CPU=arm1176
ENV PIP_CACHE_DIR=/pip-cache
WORKDIR /work
CMD ["bash"]
