#!/usr/bin/env bash
set -e

RUNNER="${HOME}/franka_direct_control/build/franka_action_runner"

if [ ! -x "$RUNNER" ]; then
  echo "ERROR: 找不到 $RUNNER"
  echo "请先运行 ./08_build_franka_direct_control.sh"
  exit 1
fi

if [ -z "$FRANKA_ROBOT_IP" ]; then
  echo "请先设置机械臂 IP，例如："
  echo "  export FRANKA_ROBOT_IP=172.16.0.2"
  exit 1
fi

echo "只测试连接和 readOnce，不执行运动。"
"$RUNNER" --command home --execute

