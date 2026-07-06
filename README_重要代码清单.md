# 作品重要代码清单

作品名称：基于RDK X5的深度相机对工业生产物料的检测和分拣

本压缩包用于提交“作品重要代码”，不包含学校名称和指导老师信息。

当前演示版本完成的核心功能是：RDK X5 识别快递盒和快递袋，结合语音指令或默认规则生成分拣命令，Ubuntu/Franka 端接收命令并执行左右分拣动作。

## rdk_voice_vision

RDK X5 端语音视觉服务相关脚本，包括语音识别、摄像头调用、YOLO 模型部署、语音播报、RDK 到 Ubuntu 指令发送等。

## yolo_tools

数据集检查、YOLO 标注器、训练数据划分和数据配置文件。当前演示重点使用 box、bag 两类。

## ubuntu_franka_bridge

Ubuntu 端 ROS 2 桥接节点和 libfranka 控制程序。RDK 发送高层命令后，该部分负责把命令转换为机械臂动作。

## franka_entity_restore

实体 Ubuntu 环境恢复脚本，包括 libfranka 编译、ROS 2 工作空间编译、Franka 网络配置、读取关节状态和实时权限说明。

## model_package_meta

RDK 模型部署说明、类别文件和模型哈希信息。

