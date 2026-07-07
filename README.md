# Franka RDK Package Sorting

English | [简体中文](README_CN.md)

This repository contains the core code for a package sorting demo built with an RDK X5 edge device, a depth/RGB camera workflow, voice interaction scripts, YOLO-based object detection, and an Ubuntu computer connected to a Franka robot arm.

The current demo recognizes package boxes and bags on the RDK X5 side, combines the visual result with voice commands or default sorting rules, sends a high-level sorting command to Ubuntu, and lets the Franka-side bridge execute left/right/front/back sorting actions through ROS 2 and libfranka-based control code.

## Project Layout

```text
.
|-- rdk_voice_vision/        RDK X5 voice, vision, model deployment, and robot-command scripts
|-- yolo_tools/              Dataset checking, annotation, split, and YOLO data configuration tools
|-- model_package_meta/      ONNX model package, class list, model metadata, and deployment notes
|-- ubuntu_franka_bridge/    Ubuntu ROS 2 bridge and libfranka direct-control programs
|-- franka_entity_restore/   Physical Ubuntu/Franka environment restore and verification scripts
`-- README_重要代码清单.md     Original Chinese code-submission inventory
```

## Main Workflow

1. RDK X5 runs the voice and vision service.
2. The camera/YOLO pipeline detects package types such as `box` and `bag`.
3. Voice input or the default rule set decides the target sorting direction.
4. RDK sends an HTTP command to the Ubuntu bridge.
5. Ubuntu receives the command through the ROS 2 bridge.
6. The Franka direct-control program maps the command to calibrated joint poses.
7. The robot executes the corresponding sorting action only when real execution is explicitly enabled.

## RDK X5 Side

Important files live in `rdk_voice_vision/`.

Common entry points include:

```text
deploy_vision_voice_assistant.py          Vision + voice assistant service
deploy_rdk_conversation_sorting_daemon.py Conversation-based sorting daemon
deploy_fast_voice_sorting_daemon.py       Fast voice sorting daemon
deploy_robot_bridge.py                    RDK-to-Ubuntu command bridge helper
upload_latest_package_model.py            Model upload helper
```

The model package is stored in `model_package_meta/`:

```text
package_sort_best.onnx
classes.txt
model_info.json
latest_model_sha256.txt
```

The model class order is:

```text
0 box
1 bag
2 shipping_label
3 barcode
```

Do not change this order unless the model has been retrained with a different class order.

## Ubuntu and Franka Side

Important files live in `ubuntu_franka_bridge/`.

The ROS 2 bridge package is:

```text
ubuntu_franka_bridge/rdk_franka_bridge/
```

The libfranka direct-control program is:

```text
ubuntu_franka_bridge/franka_direct_control/
```

The action pose configuration is:

```text
ubuntu_franka_bridge/franka_direct_control/config/actions.conf
```

The current poses in `actions.conf` are placeholder-like safe poses. Replace `pick`, `drop`, and `flip` poses with calibrated values from the real workspace before real robot execution.

## Quick Start

On Ubuntu, enter the bridge folder and make the scripts executable:

```bash
cd ubuntu_franka_bridge
chmod +x *.sh
```

Install dependencies, ROS 2 Humble components, the local libfranka package, and build the bridge:

```bash
./01_install_everything.sh
```

Rebuild the workspace after code changes:

```bash
./02_build_workspace.sh
```

Start the HTTP command server that receives RDK commands:

```bash
./03_run_rdk_bridge.sh
```

In another terminal, start the command executor:

```bash
source ~/.bashrc
ros2 run rdk_franka_bridge command_executor
```

Test the command path locally:

```bash
./04_test_rdk_command.sh
```

Test the Franka direct-control program in dry-run mode:

```bash
./09_test_franka_direct_dry_run.sh
```

Read the current Franka joint state without moving the robot:

```bash
export FRANKA_ROBOT_IP=172.16.0.2
./15_read_current_joints.sh
```

Calibrate and save a joint pose:

```bash
export FRANKA_ROBOT_IP=172.16.0.2
./14_calibrate_joint_pose.sh
```

## Safety Notes

Real robot execution is disabled by default. Dry-run mode prints the intended action without driving the robot.

Before enabling real motion, confirm all of the following:

- The emergency stop is reachable.
- Franka FCI is enabled.
- The robot status is ready.
- The workspace is clear of people and obstacles.
- The joint poses in `actions.conf` have been calibrated and verified.
- The first real test uses very small, slow movements.

To enable real execution, both variables must be set intentionally:

```bash
export FRANKA_ROBOT_IP=172.16.0.2
export FRANKA_EXECUTE_REAL=1
```

For auto-start services, check:

```bash
ubuntu_franka_bridge/11_install_autostart_services.sh
ubuntu_franka_bridge/12_disable_autostart_services.sh
```

The service environment file is:

```text
~/.config/rdk_franka_bridge.env
```

Keep `FRANKA_EXECUTE_REAL=0` until the real robot workflow has been manually tested.

## Useful Documentation

- `README_CN.md`: Chinese project overview.
- `README_重要代码清单.md`: original Chinese submission inventory.
- `ubuntu_franka_bridge/00_README_先看这个.md`: Ubuntu bridge setup notes.
- `ubuntu_franka_bridge/13_终端命令大全.md`: terminal command reference.
- `ubuntu_franka_bridge/05_真实机械臂接入说明.md`: real Franka integration notes.
- `model_package_meta/README_RDK_DEPLOY.md`: RDK model deployment notes.
- `franka_entity_restore/00_README_先看这个.md`: physical Ubuntu/Franka environment restore notes.

## Repository Status

This repository is intended to keep the important project code, scripts, configuration files, and model metadata needed to reproduce the demo. Generated build folders such as `build/`, `install/`, and `log/` are ignored by Git.
