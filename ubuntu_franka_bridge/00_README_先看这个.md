# Franka + ROS 2 + RDK 国内源安装包

这个文件夹用于 Ubuntu 控制电脑。

目标：

- 安装编译器和 ROS 2 Humble。
- 安装本地 `libfranka` 离线包。
- 创建并编译 `rdk_franka_bridge`。
- 让 RDK X5 通过 HTTP 给 Ubuntu 发送机械臂高层指令。

重要原则：

- 安装脚本不使用海外代码仓库安装路径。
- ROS 2 apt 源使用国内镜像。
- `libfranka` 使用本文件夹里的本地 `.deb` 包。
- `franka_ros2` 不是必须项。如果你们没有 `franka_ros2` 源码，脚本会跳过它，仍然可以完成 ROS 2 + libfranka + RDK 指令桥接。
- 没有 `franka_ros2` 时，后续真实控制机械臂走 `libfranka` 直接控制路线：RDK 发高层命令，Ubuntu 的 ROS 2 节点接收命令，再调用你们自己写的 libfranka 控制程序。

## 文件说明

```text
01_install_everything.sh
安装基础编译器、ROS 2 Humble、本地 libfranka，并创建/编译 RDK 指令桥接包。

02_build_workspace.sh
编译 RDK 指令桥接工作空间。

03_run_rdk_bridge.sh
启动 Ubuntu 上的 HTTP 指令接收服务。

04_test_rdk_command.sh
在 Ubuntu 本机模拟 RDK 发指令。

05_真实机械臂接入说明.md
说明在哪里写真实机械臂动作。

06_常见错误和修复.md
说明常见安装、编译、网络问题。

07_clean_downloaded_programs.sh
清理已生成/已下载的工作空间、缓存和构建产物。

08_build_franka_direct_control.sh
编译 libfranka C++ 直接控制程序。

09_test_franka_direct_dry_run.sh
不连接真机，只测试 C++ 动作程序的 dry-run 输出。

10_test_franka_connection.sh
只连接 Franka 并读取一次状态，不执行运动。

11_install_autostart_services.sh
安装开机自启动服务。测试没问题后再运行。

12_disable_autostart_services.sh
关闭并删除开机自启动服务。

13_终端命令大全.md
整理所有常用终端命令，并标注每条命令的作用。

14_calibrate_joint_pose.sh
读取当前 Franka 关节角，并保存到动作配置文件。

15_read_current_joints.sh
只读取当前 Franka 关节角，不保存。

rdk_franka_bridge/
你们自己的 ROS 2 Python 包源码。

franka_direct_control/
你们自己的 libfranka C++ 控制程序源码。
```

## 第一次安装

在 Ubuntu 中打开本文件夹终端：

```bash
chmod +x *.sh
./01_install_everything.sh
```

如果只想重新编译：

```bash
./02_build_workspace.sh
```

## 写程序的位置

主要修改：

```bash
~/rdk_franka_ws/src/rdk_franka_bridge/rdk_franka_bridge/command_executor.py
```

这里把 RDK 的高层命令转换成真实机械臂动作。

如果没有 `franka_ros2`，也在这个文件里接入你们自己的 libfranka 控制程序。当前默认是 dry-run，只打印动作，不会直接驱动真机械臂。

libfranka C++ 程序写在：

```bash
~/franka_direct_control/src/franka_action_runner.cpp
```

默认只 dry-run。真正执行前必须显式设置：

```bash
export FRANKA_ROBOT_IP=机械臂IP
export FRANKA_EXECUTE_REAL=1
```

## 编译位置

```bash
~/rdk_franka_ws
```

编译命令：

```bash
cd ~/rdk_franka_ws
colcon build --symlink-install
source install/setup.bash
```

或者直接运行：

```bash
./02_build_workspace.sh
```

## 使用方式

终端 1：启动接收 RDK 指令的 HTTP 服务：

```bash
./03_run_rdk_bridge.sh
```

终端 2：启动命令执行节点：

```bash
source ~/.bashrc
ros2 run rdk_franka_bridge command_executor
```

终端 3：本机测试：

```bash
./04_test_rdk_command.sh
```

测试 C++ 直接控制程序 dry-run：

```bash
./09_test_franka_direct_dry_run.sh
```

只测试 Franka 连接，不运动：

```bash
export FRANKA_ROBOT_IP=172.16.0.2
./10_test_franka_connection.sh
```

读取当前关节角：

```bash
export FRANKA_ROBOT_IP=172.16.0.2
./15_read_current_joints.sh
```

标定并保存点位：

```bash
export FRANKA_ROBOT_IP=172.16.0.2
./14_calibrate_joint_pose.sh
```

## 开机自启动

确认手动运行没问题后，再安装自启动：

```bash
./11_install_autostart_services.sh
```

它会创建两个用户级 systemd 服务：

```text
rdk-command-server.service
rdk-command-executor.service
```

查看状态：

```bash
systemctl --user status rdk-command-server.service
systemctl --user status rdk-command-executor.service
```

查看日志：

```bash
journalctl --user -u rdk-command-server.service -f
journalctl --user -u rdk-command-executor.service -f
```

关闭自启动：

```bash
./12_disable_autostart_services.sh
```

安全注意：默认自启动仍然是 dry-run，不会真动机械臂。配置文件在：

```bash
~/.config/rdk_franka_bridge.env
```

只有确认安全后，才能把里面的：

```text
FRANKA_EXECUTE_REAL=0
```

改成：

```text
FRANKA_EXECUTE_REAL=1
```

## RDK 发给 Ubuntu 的地址

```text
http://Ubuntu电脑IP:5000/robot_command
```

例如：

```text
http://192.168.127.100:5000/robot_command
```
