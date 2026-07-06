#!/usr/bin/env bash
set -e

READER="${HOME}/franka_direct_control/build/franka_read_joints"

if [ ! -x "$READER" ]; then
  echo "ERROR: 找不到关节读取程序：$READER"
  echo "请先运行：./08_build_franka_direct_control.sh"
  exit 1
fi

if [ -z "$FRANKA_ROBOT_IP" ]; then
  echo "请先设置机械臂 IP，例如："
  echo "  export FRANKA_ROBOT_IP=172.16.0.2"
  exit 1
fi

"$READER" --robot-ip "$FRANKA_ROBOT_IP"

