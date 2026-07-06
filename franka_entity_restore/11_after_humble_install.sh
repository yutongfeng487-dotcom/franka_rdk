#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "== Continue Franka setup after ROS 2 Humble installation =="

if [ ! -f /opt/ros/humble/setup.bash ]; then
  echo "ERROR: ROS 2 Humble is not installed or cannot be found."
  echo "Missing: /opt/ros/humble/setup.bash"
  exit 1
fi

source /opt/ros/humble/setup.bash

if ! grep -Fq 'source /opt/ros/humble/setup.bash' "${HOME}/.bashrc"; then
  echo 'source /opt/ros/humble/setup.bash' >> "${HOME}/.bashrc"
fi

echo "ROS 2 Humble detected."
ros2 --help >/dev/null

cd "${SCRIPT_DIR}"

echo "Step 1/6: restore source code"
bash ./01_restore_src.sh

echo "Step 2/6: install dependencies"
bash ./02_install_deps.sh

echo "Step 3/6: build and install libfranka"
bash ./03_build_libfranka.sh

echo "Step 4/6: build ROS 2 workspace"
bash ./04_build_ros_workspace.sh

echo "Step 5/6: create read-joints program"
bash ./07_create_read_joints_program.sh

echo "Step 6/6: show network interfaces"
ip -br link

echo
echo "Replace <interface> with the wired interface name, then run:"
echo "  bash ./10_switch_network_ip.sh <interface> dual"
echo "  bash ./06_test_franka_network.sh"
echo "  bash ./08_run_read_joints.sh"

