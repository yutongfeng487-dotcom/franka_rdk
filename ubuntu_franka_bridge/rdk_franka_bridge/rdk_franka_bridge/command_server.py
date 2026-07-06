import json
import threading

from flask import Flask, jsonify, request
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class RdkCommandServer(Node):
    def __init__(self):
        super().__init__("rdk_command_server")
        self.publisher = self.create_publisher(String, "/rdk_robot_command", 10)
        self.get_logger().info("RDK command server ready: /rdk_robot_command")

    def publish_command(self, payload):
        msg = String()
        msg.data = json.dumps(payload, ensure_ascii=False)
        self.publisher.publish(msg)
        self.get_logger().info("Published command: " + msg.data)


def main():
    rclpy.init()
    node = RdkCommandServer()
    app = Flask(__name__)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"ok": True, "service": "rdk_franka_bridge"})

    @app.route("/robot_command", methods=["POST"])
    def robot_command():
        payload = request.get_json(force=True, silent=True) or {}
        command = str(payload.get("command", "")).strip()
        item = str(payload.get("item", "")).strip()
        target = str(payload.get("target", "")).strip()
        if not command:
            return jsonify({"ok": False, "error": "missing command"}), 400

        normalized = {
            "command": command,
            "item": item,
            "target": target,
            "source": payload.get("source", "rdk"),
        }
        node.publish_command(normalized)
        return jsonify({"ok": True, "received": normalized})

    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()
    app.run(host="0.0.0.0", port=5000)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
