#!/usr/bin/env bash
set -e

RUNNER="${HOME}/franka_direct_control/build/franka_action_runner"

if [ ! -x "$RUNNER" ]; then
  echo "ERROR: 找不到 $RUNNER"
  echo "请先运行 ./08_build_franka_direct_control.sh"
  exit 1
fi

"$RUNNER" --command flip_package --item 快递件 --target 翻面
"$RUNNER" --command sort_box --item 快递盒 --target 左边
"$RUNNER" --command sort_bag --item 快递袋 --target 右边

