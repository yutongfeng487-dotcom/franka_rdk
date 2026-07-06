#!/usr/bin/env bash
set -e

WS_DIR="${HOME}/franka_ws"

echo "== Build ROS 2 workspace =="

if [ ! -d "${WS_DIR}/src" ]; then
  echo "ERROR: ${WS_DIR}/src not found."
  echo "Run ./01_restore_src.sh first."
  exit 1
fi

if [ -f /opt/ros/humble/setup.bash ]; then
  source /opt/ros/humble/setup.bash
elif [ -f /opt/ros/jazzy/setup.bash ]; then
  source /opt/ros/jazzy/setup.bash
else
  echo "ERROR: ROS 2 Humble/Jazzy setup file not found."
  echo "Ubuntu 22.04 should install ROS 2 Humble."
  exit 1
fi

cd "${WS_DIR}"
colcon build --symlink-install

source "${WS_DIR}/install/setup.bash"

echo
echo "Check rdk package:"
ros2 pkg list | grep rdk || true

echo
echo "Check franka packages:"
ros2 pkg list | grep franka | head -30 || true

echo
echo "ROS workspace build finished."
