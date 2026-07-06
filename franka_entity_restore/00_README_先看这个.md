# 实体 Ubuntu 接管 Franka：完整恢复与测试流程

这个文件夹用于把队友虚拟机里的 Franka 环境迁移到你的实体 Ubuntu，并完成：

```text
1. 恢复 franka_ws/src 源码
2. 编译安装 libfranka
3. 编译 rdk_franka_bridge / franka_ros2 工作空间
4. 配置 Franka 网络
5. 测试 FCI 端口
6. 读取 Franka 当前关节状态
```

## 重要地址

Windows/E 盘目录：

```text
E:\Franka_Ubuntu_Setup\实体Ubuntu恢复Franka环境
```

实体 Ubuntu 推荐放置位置：

```text
~/Franka_Ubuntu_Restore
```

实体 Ubuntu 工作空间：

```text
~/franka_ws
```

Franka FCI/libfranka 控制 IP：

```text
172.16.0.2
```

昨天已经验证：

```text
172.16.0.2:1337 succeeded
```

所以后续读取状态和控制机械臂时，优先使用：

```text
172.16.0.2
```

## 第 0 步：在 E 盘文件夹内直接启动

在 Ubuntu 文件管理器中进入 E 盘的：

```text
/Franka_Ubuntu_Setup/实体Ubuntu恢复Franka环境
```

在这个文件夹空白位置右键，选择“在终端中打开”，然后只运行：

```bash
bash ./00_start_here.sh
```

它会自动：

```bash
把全部文件复制到 ~/Franka_Ubuntu_Restore
自动找到 franka_ws_src_backup.tar.gz
恢复源码到 ~/franka_ws/src
```

不需要使用 `~/Downloads` 路径，也不需要手动输入 E 盘的中文挂载路径。

完成后继续：

```text
cd ~/Franka_Ubuntu_Restore
bash ./02_install_deps.sh
bash ./03_build_libfranka.sh
bash ./04_build_ros_workspace.sh
```

## 推荐执行顺序

按顺序执行：

```bash
chmod +x *.sh

./01_restore_src.sh
./02_install_deps.sh
./03_build_libfranka.sh
./04_build_ros_workspace.sh
./05_config_network_two_ips.sh
./06_test_franka_network.sh
./07_create_read_joints_program.sh
./08_run_read_joints.sh
```

如果只是想快速切换网口 IP，可以用：

```bash
./10_switch_network_ip.sh <网卡名> dual
```

例如：

```bash
./10_switch_network_ip.sh enp3s0 dual
```

可选模式：

```text
dual  同时配置 192.168.0.100 和 172.16.0.100
x5    只配置 192.168.0.100
c2    只配置 172.16.0.100
dhcp  恢复自动获取 IP
```

如果 `08_run_read_joints.sh` 输出：

```text
q = ...
```

说明实体 Ubuntu 已经能读取 Franka 当前关节状态。

## 如果提示实时内核问题

如果出现：

```text
Running kernel does not have realtime capabilities.
```

说明还需要实体 Ubuntu 安装或切换 PREEMPT_RT 实时内核。这个问题在虚拟机里已经遇到过，实体 Ubuntu 才适合继续解决。

先运行：

```bash
uname -a
```

把输出发给 Codex，再决定实时内核安装方式。

## 安全要求

在任何真实运动前，必须确认：

```text
急停在手边
Robot Status: Enabled
FCI: ON
System: Ready
Safety Scenario: Work
机械臂周围没有人和障碍物
第一次只做极小幅度运动测试
```
