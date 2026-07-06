#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_FILE="${1:-${SCRIPT_DIR}/franka_description-2.7.0.zip}"
WS_SRC="${HOME}/franka_ws/src"
TARGET="${WS_SRC}/franka_description"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

if [ ! -f "${ZIP_FILE}" ]; then
  echo "ERROR: cannot find ${ZIP_FILE}"
  exit 1
fi

if ! command -v unzip >/dev/null 2>&1; then
  sudo apt update
  sudo apt install -y unzip
fi

mkdir -p "${WS_SRC}"
unzip -q "${ZIP_FILE}" -d "${TMP_DIR}"

SOURCE_DIR="$(find "${TMP_DIR}" -mindepth 1 -maxdepth 1 -type d -name 'franka_description*' | head -n 1)"
if [ -z "${SOURCE_DIR}" ]; then
  echo "ERROR: cannot find extracted franka_description folder"
  exit 1
fi

if [ -d "${TARGET}" ]; then
  BACKUP="${TARGET}.backup_$(date +%Y%m%d_%H%M%S)"
  echo "Existing franka_description found. Backup: ${BACKUP}"
  mv "${TARGET}" "${BACKUP}"
fi

mv "${SOURCE_DIR}" "${TARGET}"

echo "Installed source to: ${TARGET}"

if [ -f /opt/ros/humble/setup.bash ]; then
  source /opt/ros/humble/setup.bash
  cd "${HOME}/franka_ws"
  colcon build --symlink-install --packages-select franka_description
  source "${HOME}/franka_ws/install/setup.bash"
  ros2 pkg list | grep '^franka_description$' || true
else
  echo "ROS 2 Humble is not installed yet."
  echo "After Humble installation, run:"
  echo "  cd ~/franka_ws"
  echo "  source /opt/ros/humble/setup.bash"
  echo "  colcon build --symlink-install --packages-select franka_description"
fi
