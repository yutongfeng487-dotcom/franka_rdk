#!/usr/bin/env bash
set -e

source /opt/ros/humble/setup.bash

if [ -f "$HOME/franka_ros2_ws/install/setup.bash" ]; then
  source "$HOME/franka_ros2_ws/install/setup.bash"
fi

source "$HOME/rdk_franka_ws/install/setup.bash"

echo "启动 RDK HTTP 指令接收服务。"
echo "RDK 应发送到："
echo "  http://Ubuntu电脑IP:5000/robot_command"
echo
echo "另开一个终端运行执行节点："
echo "  source ~/.bashrc"
echo "  ros2 run rdk_franka_bridge command_executor"
echo

ros2 run rdk_franka_bridge command_server

