#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/Franka_Ubuntu_Restore"

echo "== Franka entity Ubuntu restore launcher =="
echo "source folder: ${SCRIPT_DIR}"
echo "target folder: ${TARGET_DIR}"

mkdir -p "${TARGET_DIR}"

if [ "${SCRIPT_DIR}" != "${TARGET_DIR}" ]; then
  echo "Copying restore package into Ubuntu home folder..."
  cp -a "${SCRIPT_DIR}/." "${TARGET_DIR}/"
fi

cd "${TARGET_DIR}"

if [ ! -f "./franka_ws_src_backup.tar.gz" ]; then
  echo "ERROR: franka_ws_src_backup.tar.gz is not in ${TARGET_DIR}"
  echo "Files currently available:"
  ls -la
  exit 1
fi

chmod +x ./*.sh 2>/dev/null || true

echo
echo "Package is ready in: ${TARGET_DIR}"
echo "Restoring source code now..."
bash ./01_restore_src.sh

echo
echo "Source restore finished. Continue with:"
echo "  cd ${TARGET_DIR}"
echo "  bash ./02_install_deps.sh"
echo "  bash ./03_build_libfranka.sh"
echo "  bash ./04_build_ros_workspace.sh"
