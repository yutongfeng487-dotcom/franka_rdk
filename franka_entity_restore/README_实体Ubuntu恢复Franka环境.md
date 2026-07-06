# 实体 Ubuntu 恢复 Franka 控制环境

这个说明用于把队友虚拟机里的 `franka_ws/src` 源码迁移到你的实体 Ubuntu。

## 你已有的压缩包

Windows 上的文件：

```text
C:\Users\青柠\Downloads\franka_ws_src_backup.tar.gz
```

压缩包里包含：

```text
src/libfranka
src/franka_ros2
src/rdk_franka_bridge
```

注意：当前压缩包里没有 `franka_description`，所以优先使用 `libfranka` 直接控制机械臂，不先依赖 `franka_bringup`。

## 第 1 步：把压缩包放到实体 Ubuntu

可以用 U 盘、共享文件夹、QQ/微信文件传输等方式，把压缩包放到实体 Ubuntu 的下载目录，例如：

```text
~/Downloads/franka_ws_src_backup.tar.gz
```

## 第 2 步：解压工作空间

在实体 Ubuntu 终端运行：

```bash
mkdir -p ~/franka_ws
tar -xzf ~/Downloads/franka_ws_src_backup.tar.gz -C ~/franka_ws
ls ~/franka_ws/src
```

应该看到：

```text
franka_ros2
libfranka
rdk_franka_bridge
```

## 第 3 步：安装基础依赖

如果实体 Ubuntu 已经安装 ROS 2 Jazzy，运行：

```bash
sudo apt update
sudo apt install -y build-essential cmake git \
  libpoco-dev libeigen3-dev libfmt-dev \
  python3-colcon-common-extensions
```

然后加载 ROS 环境：

```bash
source /opt/ros/jazzy/setup.bash
```

## 第 4 步：编译安装 libfranka

```bash
cd ~/franka_ws/src/libfranka
mkdir -p build
cd build
cmake -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTS=OFF ..
make -j$(nproc)
sudo make install
sudo ldconfig
```

检查：

```bash
ls /usr/local/include/franka
ldconfig -p | grep franka
```

能看到 `robot.h`、`exception.h`、`libfranka.so` 就说明安装成功。

## 第 5 步：编译 ROS2 工作空间

```bash
cd ~/franka_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source ~/franka_ws/install/setup.bash
```

检查 RDK 桥接包：

```bash
ros2 pkg list | grep rdk
```

应该看到：

```text
rdk_franka_bridge
```

## 第 6 步：配置 Franka 网络

如果使用一个网卡配两个 IP，并通过交换机同时连接 C2 和 X5：

```bash
sudo ip addr flush dev ens33
sudo ip addr add 192.168.0.100/24 dev ens33
sudo ip addr add 172.16.0.100/24 dev ens33
sudo ip link set ens33 up
```

注意：`ens33` 要换成实体 Ubuntu 的真实有线网卡名。查看网卡名：

```bash
ip addr
```

测试：

```bash
ping -c 4 192.168.0.1
ping -c 4 172.16.0.2
nc -vz -w 3 172.16.0.2 1337
```

昨天已经验证：FCI 端口通的是：

```text
172.16.0.2:1337
```

所以 libfranka 程序里优先使用：

```text
172.16.0.2
```

## 第 7 步：读取 Franka 当前关节

```bash
cat > /tmp/read_franka_joints.cpp <<'CPP'
#include <iostream>
#include <franka/exception.h>
#include <franka/robot.h>

int main() {
  try {
    franka::Robot robot("172.16.0.2");
    auto state = robot.readOnce();

    std::cout << "q = ";
    for (double v : state.q) {
      std::cout << v << " ";
    }
    std::cout << std::endl;
    return 0;
  } catch (const franka::Exception& e) {
    std::cerr << "Franka error: " << e.what() << std::endl;
    return 1;
  }
}
CPP

g++ /tmp/read_franka_joints.cpp -o /tmp/read_franka_joints -lfranka -pthread
sudo /tmp/read_franka_joints
```

如果提示找不到动态库，运行：

```bash
source /opt/ros/jazzy/setup.bash
source ~/franka_ws/install/setup.bash
sudo env LD_LIBRARY_PATH=$LD_LIBRARY_PATH /tmp/read_franka_joints
```

如果输出：

```text
q = ...
```

说明实体 Ubuntu 已经能读取 Franka 状态。

## 第 8 步：实时内核

虚拟机里昨天报错：

```text
Running kernel does not have realtime capabilities.
```

实体 Ubuntu 需要安装或切换到 PREEMPT_RT 实时内核后，再做真机运动控制。读取状态和小测试成功后，再继续配置实时内核和低速安全运动。

## 安全提醒

真机运动前必须确认：

```text
急停在手边
Robot Status: Enabled
FCI: ON
System: Ready
Safety Scenario: Work
机械臂周围没有人和障碍物
第一次运动只做极小幅度测试
```
