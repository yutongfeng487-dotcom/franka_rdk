#!/usr/bin/env bash
set -e

echo "== Install basic dependencies =="

if [ -f /opt/ros/humble/setup.bash ]; then
  ROS_DISTRO_NAME="humble"
elif [ -f /opt/ros/jazzy/setup.bash ]; then
  ROS_DISTRO_NAME="jazzy"
else
  ROS_DISTRO_NAME=""
  echo "WARNING: ROS 2 Humble/Jazzy was not found."
  echo "Ubuntu 22.04 should install ROS 2 Humble first."
fi

sudo apt update
sudo apt install -y \
  build-essential \
  cmake \
  git \
  libpoco-dev \
  libeigen3-dev \
  libfmt-dev \
  python3-colcon-common-extensions \
  netcat-openbsd

echo
if [ -n "${ROS_DISTRO_NAME}" ]; then
  echo "Detected ROS 2: ${ROS_DISTRO_NAME}"
fi
echo "Dependency install finished."
