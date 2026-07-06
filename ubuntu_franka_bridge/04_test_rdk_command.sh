#!/usr/bin/env bash
set -e

echo "测试本机 RDK 指令桥。"
echo "请先在另一个终端运行：./03_run_rdk_bridge.sh"

curl -s -X POST http://127.0.0.1:5000/robot_command \
  -H "Content-Type: application/json" \
  -d '{"command":"flip_package","item":"快递件","target":"翻面","source":"local_test"}'

echo
echo "如果 command_executor 正在运行，应看到 dry-run 翻面日志。"

