
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

apt update
apt install -y \
  autoconf \
  automake \
  libavcodec-dev \
  libavdevice-dev \
  libavfilter-dev \
  libavformat-dev \
  libavutil-dev \
  libfreetype6-dev \
  libjpeg-dev \
  liblcms2-dev \
  libopenjp2-7-dev \
  libswresample-dev \
  libswscale-dev \
  libtiff-dev \
  libtool \
  libwebp-dev \
  m4 \
  pkg-config \
  zlib1g-dev \

cat >/etc/pip.conf <<EOF
[global]
index-url = https://pypi.org/simple
extra-index-url = https://www.piwheels.org/simple
find-links = file:///$GIT_ROOT/legacy/raspi0/wheels
EOF

# TODO: Not sure which is actually needed - but one worked to multithread the build for numpy
export NPY_NUM_BUILD_JOBS="$(nproc)"
export MAKEFLAGS="-j$(nproc)"
export CMAKE_BUILD_PARALLEL_LEVEL="$(nproc)"

#uvx pip install --find-links /work/legacy/raspi0/wheels sendspin
uvx pip install sendspin \
  --index-url https://pypi.org/simple \
  --extra-index-url https://www.piwheels.org/simple \
  --find-links file:///work/legacy/raspi0/wheels \
  --only-binary=:all:



find /root/.cache/uv -path "*sdists-*" -type f -name "*.whl" \
  -exec cp -u -t /work/legacy/raspi0/wheels {} +

git add .
git commit -m "sendspin wheel rebuild $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
git push
echo "Sendspin wheel rebuild complete."
