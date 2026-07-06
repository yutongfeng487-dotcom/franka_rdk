#!/usr/bin/env bash
set -e

echo "这个脚本会清理本安装包生成/下载的内容："
echo
echo "  ~/rdk_franka_ws"
echo "  ~/franka_ros2_ws"
echo "  ~/franka_direct_control"
echo "  ~/.cache/pip"
echo "  ~/.ros/rosdep"
echo "  /var/cache/apt/archives 中的 apt 缓存"
echo
echo "不会删除当前 E 盘/数据盘上的 Franka_Ubuntu_Setup 文件夹。"
echo "不会格式化磁盘。"
echo
read -r -p "确认清理请输入 YES： " answer

if [ "$answer" != "YES" ]; then
  echo "已取消。"
  exit 0
fi

echo "停止可能正在运行的桥接进程..."
pkill -f "rdk_franka_bridge.command_server" || true
pkill -f "rdk_franka_bridge.command_executor" || true

echo "删除工作空间..."
rm -rf "$HOME/rdk_franka_ws"
rm -rf "$HOME/franka_ros2_ws"
rm -rf "$HOME/franka_direct_control"

echo "删除用户缓存..."
rm -rf "$HOME/.cache/pip"
rm -rf "$HOME/.ros/rosdep"

echo "清理 apt 缓存..."
sudo apt clean
sudo rm -rf /var/cache/apt/archives/*.deb || true

echo "清理完成。"
