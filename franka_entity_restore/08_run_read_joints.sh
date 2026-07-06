#!/usr/bin/env bash
set -e

BIN="/tmp/read_franka_joints"

echo "== Run Franka read joints test =="

if [ ! -x "${BIN}" ]; then
  echo "ERROR: ${BIN} not found."
  echo "Run ./07_create_read_joints_program.sh first."
  exit 1
fi

if [ -f /opt/ros/humble/setup.bash ]; then
  source /opt/ros/humble/setup.bash
elif [ -f /opt/ros/jazzy/setup.bash ]; then
  source /opt/ros/jazzy/setup.bash
fi

if [ -f "${HOME}/franka_ws/install/setup.bash" ]; then
  source "${HOME}/franka_ws/install/setup.bash"
fi

echo "Running with sudo and current LD_LIBRARY_PATH."
sudo env LD_LIBRARY_PATH="${LD_LIBRARY_PATH}" "${BIN}"
