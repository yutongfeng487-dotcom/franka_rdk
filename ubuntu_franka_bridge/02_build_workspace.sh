#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIDGE_SRC_IN_SETUP="${SCRIPT_DIR}/rdk_franka_bridge"
WORKSPACE="${HOME}/rdk_franka_ws"
BRIDGE_DST="${WORKSPACE}/src/rdk_franka_bridge"

if [ ! -f /opt/ros/humble/setup.bash ]; then
  echo "ERROR: ROS 2 Humble 未安装。"
  echo "缺少：/opt/ros/humble/setup.bash"
  echo "请先运行 ./01_install_everything.sh"
  exit 1
fi

if [ ! -d "$BRIDGE_SRC_IN_SETUP" ]; then
  echo "ERROR: 当前安装包缺少 rdk_franka_bridge 源码目录："
  echo "  $BRIDGE_SRC_IN_SETUP"
  exit 1
fi

mkdir -p "${WORKSPACE}/src"

if [ ! -d "$BRIDGE_DST" ]; then
  echo "复制 rdk_franka_bridge 到 ROS 2 工作空间..."
  cp -r "$BRIDGE_SRC_IN_SETUP" "$BRIDGE_DST"
else
  echo "工作空间已有 rdk_franka_bridge，保留现有版本："
  echo "  $BRIDGE_DST"
fi

source /opt/ros/humble/setup.bash

if [ -f "$HOME/franka_ros2_ws/install/setup.bash" ]; then
  source "$HOME/franka_ros2_ws/install/setup.bash"
fi

cd "$WORKSPACE"

echo "检测工作空间中的 ROS 2 包："
find src -mindepth 2 -maxdepth 2 -name package.xml -print

if ! find src -mindepth 2 -maxdepth 2 -name package.xml | grep -q .; then
  echo "ERROR: 没有找到 ROS 2 包。不能继续编译。"
  exit 1
fi

colcon build --symlink-install
source install/setup.bash

echo "编译完成。"
echo "工作空间：$WORKSPACE"
echo "代码位置：$BRIDGE_DST/rdk_franka_bridge/"

