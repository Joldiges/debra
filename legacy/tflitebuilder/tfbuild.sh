#!/bin/bash
set -e

echo "=== TensorFlow Lite ARM32 Conservative Build Script ==="
echo "Optimized for reliability and compatibility with Raspberry Pi Zero"
echo ""

# Configuration
TFLITE_VERSION="v2.14.0"
BUILD_DIR="/tmp/tflite_build"
OUTPUT_DIR="/tmp/tflite_output"

# Detect number of cores
CORES=$(nproc)
BUILD_JOBS=$((CORES > 1 ? CORES - 1 : 1))

echo "Configuration:"
echo "  TensorFlow Lite version: $TFLITE_VERSION"
echo "  Build directory: $BUILD_DIR"
echo "  Output directory: $OUTPUT_DIR"
echo "  CPU cores available: $CORES"
echo "  Build jobs: $BUILD_JOBS"
echo ""

# Check architecture
echo "=== Checking System ==="
uname -a
echo "Architecture: $(uname -m)"
echo ""

# Install dependencies
echo "=== Installing Dependencies ==="
apt-get update
apt-get install -y \
    file \
    git \
    cmake \
    build-essential \
    wget \
    unzip \
    python3 \
    python3-pip \
    python3-numpy \
    xxd \
    curl

echo ""

# Create build directory
echo "=== Setting up Build Directory ==="
mkdir -p "$BUILD_DIR"
mkdir -p "$OUTPUT_DIR"
cd "$BUILD_DIR"

# Clone TensorFlow
echo "=== Cloning TensorFlow Repository ==="
if [ ! -d "tensorflow" ]; then
    git clone --depth 1 --branch "$TFLITE_VERSION" https://github.com/tensorflow/tensorflow.git
    echo "Cloned TensorFlow $TFLITE_VERSION"
else
    echo "TensorFlow repository already exists"
fi

cd tensorflow

# Build TensorFlow Lite
echo ""
echo "=== Building TensorFlow Lite C Library ==="
echo "Using conservative flags known to work on ARMv6..."
echo "Building with $BUILD_JOBS parallel jobs..."
echo ""

mkdir -p build
cd build

# Conservative CMake configuration
# - No XNNPACK (may not support ARMv6 without NEON)
# - Standard optimization flags
# - Explicit ARMv6 targeting
cmake ../tensorflow/lite/c \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_FLAGS="-O3 -march=armv6 -mfpu=vfp -mfloat-abi=hard" \
    -DCMAKE_CXX_FLAGS="-O3 -march=armv6 -mfpu=vfp -mfloat-abi=hard" \
    -DTFLITE_ENABLE_XNNPACK=OFF \
    -DCMAKE_SYSTEM_PROCESSOR=armv6l

# Build
echo "Building..."
make -j$BUILD_JOBS

echo ""
echo "=== Build Complete ==="
echo ""

# Find and copy the library
BUILT_LIB=$(find . -name "libtensorflowlite_c.so" -type f | head -1)

if [ -n "$BUILT_LIB" ]; then
    cp "$BUILT_LIB" "$OUTPUT_DIR/"
    echo "Library copied to: $OUTPUT_DIR/libtensorflowlite_c.so"
    echo ""
    echo "=== Library Info ==="
    file "$OUTPUT_DIR/libtensorflowlite_c.so"
    ls -lh "$OUTPUT_DIR/libtensorflowlite_c.so"
    
    # Strip debug symbols
    echo ""
    echo "=== Stripping Debug Symbols ==="
    strip "$OUTPUT_DIR/libtensorflowlite_c.so"
    echo "Stripped library size:"
    ls -lh "$OUTPUT_DIR/libtensorflowlite_c.so"
    
    echo ""
    echo "=== Verification ==="
    file "$OUTPUT_DIR/libtensorflowlite_c.so"
    
    echo ""
    echo "=== Success! ==="
    echo "Library built successfully at: $OUTPUT_DIR/libtensorflowlite_c.so"
    echo ""
    echo "Next steps:"
    echo "  1. Copy from container: docker cp <container>:/tmp/tflite_output/libtensorflowlite_c.so ./"
    echo "  2. Transfer to Pi: scp libtensorflowlite_c.so oldiges@debra:/tmp/"
    echo "  3. Install: sudo cp /tmp/libtensorflowlite_c.so /opt/debra/linux-voice-assistant/.venv/lib/python3.13/site-packages/pymicro_wakeword/lib/"
else
    echo "ERROR: Build succeeded but library not found!"
    echo "Searching for library files..."
    find . -name "*.so" -name "*tensorflow*"
    exit 1
fi

