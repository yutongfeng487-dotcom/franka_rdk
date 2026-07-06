#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="${SCRIPT_DIR}/franka_direct_control"
DST="${HOME}/franka_direct_control"

if [ ! -d "$SRC" ]; then
  echo "ERROR: 缺少 franka_direct_control 源码目录：$SRC"
  exit 1
fi

if [ ! -d "$DST" ]; then
  cp -r "$SRC" "$DST"
else
  echo "已存在 $DST，保留现有代码，不覆盖。"
  mkdir -p "$DST/config"
  if [ ! -f "$DST/config/actions.conf" ]; then
    cp "$SRC/config/actions.conf" "$DST/config/actions.conf"
  fi
fi

mkdir -p "$DST/build"
cd "$DST/build"
cmake ..
cmake --build . -j"$(nproc)"

echo "编译完成："
echo "  $DST/build/franka_action_runner"
echo
echo "dry-run 测试："
echo "  $DST/build/franka_action_runner --command flip_package --item 快递件 --target 翻面"
