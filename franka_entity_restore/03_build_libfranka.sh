#!/usr/bin/env bash
set -e

LIBFRANKA_DIR="${HOME}/franka_ws/src/libfranka"

echo "== Build and install libfranka =="
echo "source: ${LIBFRANKA_DIR}"

if [ ! -d "${LIBFRANKA_DIR}" ]; then
  echo "ERROR: ${LIBFRANKA_DIR} not found."
  echo "Run ./01_restore_src.sh first."
  exit 1
fi

cd "${LIBFRANKA_DIR}"

if [ -f build/CMakeCache.txt ]; then
  OLD_BUILD="build.backup_$(date +%Y%m%d_%H%M%S)"
  echo "Old CMake cache found. Moving build directory to ${OLD_BUILD}"
  mv build "${OLD_BUILD}"
fi

mkdir -p build
cd build

cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF ..
make -j"$(nproc)"
sudo make install
sudo ldconfig

echo
echo "Installed libfranka headers:"
ls /usr/local/include/franka | head

echo
echo "Installed libfranka library:"
ldconfig -p | grep franka || true

echo
echo "libfranka build/install finished."
