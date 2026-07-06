import json
import os
import subprocess

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class RdkCommandExecutor(Node):
    def __init__(self):
        super().__init__("rdk_command_executor")
        self.sub = self.create_subscription(String, "/rdk_robot_command", self.on_command, 10)
        self.runner = os.environ.get(
            "FRANKA_ACTION_RUNNER",
            os.path.expanduser("~/franka_direct_control/build/franka_action_runner"),
        )
        self.execute_real = os.environ.get("FRANKA_EXECUTE_REAL", "0") == "1"
        self.robot_ip = os.environ.get("FRANKA_ROBOT_IP", "")
        self.action_config = os.environ.get(
            "FRANKA_ACTION_CONFIG",
            os.path.expanduser("~/franka_direct_control/config/actions.conf"),
        )
        mode = "REAL EXECUTE" if self.execute_real else "SAFE DRY-RUN"
        self.get_logger().info(f"RDK command executor started in {mode} mode.")
        self.get_logger().info(f"Action runner: {self.runner}")

    def on_command(self, msg):
        try:
            payload = json.loads(msg.data)
        except Exception as exc:
            self.get_logger().error(f"Bad command JSON: {exc}")
            return

        command = payload.get("command", "")
        item = payload.get("item", "")
        target = payload.get("target", "")
        self.get_logger().info(f"Received command={command}, item={item}, target={target}")

        self.run_action(command, item, target)

    def run_action(self, command, item, target):
        if not os.path.exists(self.runner):
            self.get_logger().error(f"franka_action_runner not found: {self.runner}")
            return

        args = [
            self.runner,
            "--command", command,
            "--item", item,
            "--target", target,
            "--config", self.action_config,
        ]
        if self.robot_ip:
            args += ["--robot-ip", self.robot_ip]
        if self.execute_real:
            args += ["--execute"]

        self.get_logger().info("Running: " + " ".join(args))
        completed = subprocess.run(args, text=True, capture_output=True)
        if completed.stdout:
            self.get_logger().info(completed.stdout.strip())
        if completed.stderr:
            self.get_logger().error(completed.stderr.strip())
        if completed.returncode != 0:
            self.get_logger().error(f"Action runner failed with code {completed.returncode}")


def main():
    rclpy.init()
    node = RdkCommandExecutor()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
