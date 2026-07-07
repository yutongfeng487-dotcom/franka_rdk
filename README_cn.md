# Franka RDK 快递包裹分拣项目

[English](README.md) | 简体中文

本仓库保存“基于 RDK X5 的深度相机对工业生产物料的检测和分拣”项目的重要代码。项目包含 RDK X5 端的语音视觉脚本、YOLO 目标检测模型部署、RDK 到 Ubuntu 的指令发送逻辑，以及 Ubuntu/Franka 端的 ROS 2 桥接和 libfranka 机械臂控制程序。

当前演示版本的核心流程是：RDK X5 识别快递盒和快递袋，结合语音指令或默认分拣规则生成高层分拣命令，发送给 Ubuntu 端；Ubuntu 端接收命令后，由 ROS 2 桥接节点和 libfranka 控制程序执行左右/前后分拣动作。

## 目录结构

```text
.
|-- rdk_voice_vision/        RDK X5 端语音、视觉、模型部署和机械臂指令发送脚本
|-- yolo_tools/              数据集检查、YOLO 标注、训练集划分和 data.yaml 生成工具
|-- model_package_meta/      ONNX 模型、类别文件、模型信息和 RDK 部署说明
|-- ubuntu_franka_bridge/    Ubuntu 端 ROS 2 桥接节点和 libfranka 直接控制程序
|-- franka_entity_restore/   实体 Ubuntu/Franka 环境恢复、编译和测试脚本
`-- README_重要代码清单.md     原始中文重要代码清单
```

## 总体流程

1. RDK X5 启动语音视觉服务。
2. 摄像头和 YOLO 检测流程识别 `box`、`bag` 等包裹类别。
3. 程序根据语音指令或默认规则决定分拣方向。
4. RDK 通过 HTTP 向 Ubuntu 端发送高层命令。
5. Ubuntu 端 ROS 2 桥接节点接收命令。
6. Franka 直接控制程序把命令映射到已标定的关节动作点位。
7. 只有显式开启真实执行开关后，机械臂才会执行真实运动。

## RDK X5 端

主要代码位于 `rdk_voice_vision/`

常用入口文件包括：

```text
deploy_vision_voice_assistant.py          视觉 + 语音助手服务
deploy_rdk_conversation_sorting_daemon.py 对话式分拣守护进程
deploy_fast_voice_sorting_daemon.py       快速语音分拣守护进程
deploy_robot_bridge.py                    RDK 到 Ubuntu 的指令桥接辅助脚本
upload_latest_package_model.py            模型上传辅助脚本
```

模型包位于 `model_package_meta/`：

```text
package_sort_best.onnx
classes.txt
model_info.json
latest_model_sha256.txt
```

当前模型类别顺序为：

```text
0 box
1 bag
2 shipping_label
3 barcode
```

除非重新训练模型并修改输出顺序，否则不要更改这个类别顺序。

## Ubuntu 和 Franka 端

主要代码位于 `ubuntu_franka_bridge/`。

ROS 2 桥接包路径：

```text
ubuntu_franka_bridge/rdk_franka_bridge/
```

libfranka 直接控制程序路径：

```text
ubuntu_franka_bridge/franka_direct_control/
```

动作点位配置文件：

```text
ubuntu_franka_bridge/franka_direct_control/config/actions.conf
```

当前 `actions.conf` 中的点位是偏安全的占位点位，不是最终真实分拣点位。真实运行前必须用现场工作空间重新标定 `pick`、`drop`、`flip` 等动作点位。

## 快速开始

在 Ubuntu 中进入桥接目录，并给脚本添加执行权限：

```bash
cd ubuntu_franka_bridge
chmod +x *.sh
```

安装依赖、ROS 2 Humble 相关组件、本地 libfranka 包，并编译桥接程序：

```bash
./01_install_everything.sh
```

修改代码后重新编译：

```bash
./02_build_workspace.sh
```

启动接收 RDK 命令的 HTTP 服务：

```bash
./03_run_rdk_bridge.sh
```

另开一个终端，启动命令执行节点：

```bash
source ~/.bashrc
ros2 run rdk_franka_bridge command_executor
```

在 Ubuntu 本机模拟 RDK 命令：

```bash
./04_test_rdk_command.sh
```

以 dry-run 模式测试 Franka 直接控制程序，不驱动真实机械臂：

```bash
./09_test_franka_direct_dry_run.sh
```

只读取当前 Franka 关节状态，不执行运动：

```bash
export FRANKA_ROBOT_IP=172.16.0.2
./15_read_current_joints.sh
```

读取并保存当前关节点位，用于标定动作配置：

```bash
export FRANKA_ROBOT_IP=172.16.0.2
./14_calibrate_joint_pose.sh
```

## 安全注意

默认情况下，真实机械臂执行是关闭的。dry-run 模式只打印将要执行的动作，不会驱动机械臂。

真实运行前必须确认：

- 急停按钮在手边。
- Franka FCI 已开启。
- 机械臂状态为 Ready。
- 工作空间内没有人员和障碍物。
- `actions.conf` 中的动作点位已经完成现场标定和验证。
- 第一次真实测试只做小幅、低速运动。

启用真实执行时，必须显式设置：

```bash
export FRANKA_ROBOT_IP=172.16.0.2
export FRANKA_EXECUTE_REAL=1
```

开机自启动服务相关脚本：

```bash
ubuntu_franka_bridge/11_install_autostart_services.sh
ubuntu_franka_bridge/12_disable_autostart_services.sh
```

自启动服务环境配置文件：

```text
~/.config/rdk_franka_bridge.env
```

在人工完整测试通过前，请保持：

```text
FRANKA_EXECUTE_REAL=0
```

## 相关文档

- `README.md`：英文项目说明。
- `README_重要代码清单.md`：原始中文重要代码清单。
- `ubuntu_franka_bridge/00_README_先看这个.md`：Ubuntu 桥接环境说明。
- `ubuntu_franka_bridge/13_终端命令大全.md`：常用终端命令大全。
- `ubuntu_franka_bridge/05_真实机械臂接入说明.md`：真实 Franka 接入说明。
- `model_package_meta/README_RDK_DEPLOY.md`：RDK 模型部署说明。
- `franka_entity_restore/00_README_先看这个.md`：实体 Ubuntu/Franka 环境恢复说明。

## 仓库说明

本仓库用于保存复现实验演示所需的重要源码、脚本、配置文件和模型元信息。`build/`、`install/`、`log/` 等生成目录已经通过 `.gitignore` 排除，不建议提交到 Git。
