#!/usr/bin/env bash
set -e

echo "== Franka + ROS 2 + RDK 国内源安装 =="
echo "推荐系统：Ubuntu 22.04 + ROS 2 Humble"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODENAME="$(lsb_release -cs)"

if [ "$CODENAME" != "jammy" ]; then
  echo "WARNING: 当前系统不是 Ubuntu 22.04 jammy。"
  echo "检测到：$CODENAME"
  read -r -p "是否继续？[y/N] " answer
  case "$answer" in
    y|Y|yes|YES) ;;
    *) echo "已停止。"; exit 1 ;;
  esac
fi

echo "== 1. 配置 Ubuntu 国内 apt 源 =="
sudo cp /etc/apt/sources.list "/etc/apt/sources.list.backup.$(date +%Y%m%d_%H%M%S)"
sudo tee /etc/apt/sources.list >/dev/null <<EOF
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ ${CODENAME} main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ ${CODENAME}-updates main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ ${CODENAME}-backports main restricted universe multiverse
deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ ${CODENAME}-security main restricted universe multiverse
EOF

sudo apt update

echo "== 2. 安装编译器和基础工具 =="
sudo apt install -y \
  build-essential \
  gcc \
  g++ \
  make \
  cmake \
  git \
  wget \
  curl \
  gnupg \
  lsb-release \
  software-properties-common \
  python3 \
  python3-pip \
  python3-venv \
  net-tools \
  iproute2 \
  ethtool \
  chrony

echo "== 3. 安装 libfranka 依赖 =="
sudo apt install -y libpoco-dev libfmt-dev libeigen3-dev

echo "== 4. 安装本地 libfranka 离线包 =="
LIBFRANKA_DEB="${SCRIPT_DIR}/02_libfranka_0.19.0_ubuntu22.04_jammy_amd64.deb"
if [ ! -f "$LIBFRANKA_DEB" ]; then
  echo "ERROR: 未找到本地 libfranka 安装包："
  echo "  $LIBFRANKA_DEB"
  echo "请把 libfranka .deb 放到当前文件夹后再运行。"
  exit 1
fi

sudo dpkg -i "$LIBFRANKA_DEB" || true
sudo apt --fix-broken install -y
sudo ldconfig
dpkg -l | grep libfranka || true

echo "== 5. 配置 ROS 2 Humble 国内 apt 源 =="
sudo mkdir -p /etc/apt/keyrings

if [ -f "${SCRIPT_DIR}/ros-archive-keyring.gpg" ]; then
  sudo cp "${SCRIPT_DIR}/ros-archive-keyring.gpg" /etc/apt/keyrings/ros-archive-keyring.gpg
else
  echo "未找到本地 ros-archive-keyring.gpg，尝试从国内镜像获取 key。"
  curl -fsSL https://mirrors.tuna.tsinghua.edu.cn/rosdistro/ros.key \
    | sudo gpg --dearmor -o /etc/apt/keyrings/ros-archive-keyring.gpg
fi

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/ros-archive-keyring.gpg] https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu/ ${CODENAME} main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null

sudo apt update
sudo apt install -y \
  ros-humble-desktop \
  ros-dev-tools \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-vcstool \
  python3-flask

if ! grep -q "source /opt/ros/humble/setup.bash" "$HOME/.bashrc"; then
  echo "source /opt/ros/humble/setup.bash" >> "$HOME/.bashrc"
fi

source /opt/ros/humble/setup.bash

echo "== 6. 可选：编译本地 franka_ros2 源码 =="
if [ -d "${SCRIPT_DIR}/franka_ros2_src" ]; then
  mkdir -p "$HOME/franka_ros2_ws"
  rm -rf "$HOME/franka_ros2_ws/src"
  cp -r "${SCRIPT_DIR}/franka_ros2_src" "$HOME/franka_ros2_ws/src"
  cd "$HOME/franka_ros2_ws"
  rosdep install --from-paths src --ignore-src --rosdistro humble -y || true
  colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF
  if ! grep -q "source $HOME/franka_ros2_ws/install/setup.bash" "$HOME/.bashrc"; then
    echo "source $HOME/franka_ros2_ws/install/setup.bash" >> "$HOME/.bashrc"
  fi
else
  echo "未发现 franka_ros2_src/，跳过 franka_ros2 源码编译。"
  echo "这不影响先编译 RDK 指令桥接包。"
fi

echo "== 7. 创建并编译 RDK 指令桥接包 =="
"${SCRIPT_DIR}/02_build_workspace.sh"

echo "== 8. 编译 libfranka 直接控制程序 =="
"${SCRIPT_DIR}/08_build_franka_direct_control.sh"

echo
echo "安装完成。"
echo "程序位置："
echo "  $HOME/rdk_franka_ws/src/rdk_franka_bridge/rdk_franka_bridge/"
echo "libfranka C++ 控制程序："
echo "  $HOME/franka_direct_control/build/franka_action_runner"
echo
echo "启动接收服务："
echo "  ${SCRIPT_DIR}/03_run_rdk_bridge.sh"
