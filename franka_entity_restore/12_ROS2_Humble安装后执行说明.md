# ROS 2 Humble 安装完成后

实体系统是 Ubuntu 22.04.5，应安装 ROS 2 Humble。

先验证：

```bash
test -f /opt/ros/humble/setup.bash && echo "Humble 已安装" || echo "Humble 未安装"
```

如果已安装：

```bash
source /opt/ros/humble/setup.bash
ros2 --help
```

然后在 `实体Ubuntu恢复Franka环境` 文件夹内打开终端，运行：

```bash
bash ./11_after_humble_install.sh
```

完成后，根据脚本显示的有线网卡名称，例如 `enp3s0`，运行：

```bash
bash ./10_switch_network_ip.sh enp3s0 dual
bash ./06_test_franka_network.sh
bash ./08_run_read_joints.sh
```

Franka FCI 地址已写入脚本：

```text
172.16.0.2:1337
```
