import sys

sys.path.insert(0, "pydeps")

import paramiko


HOST = "192.168.127.10"
USER = "root"
PASSWORD = "root"
REMOTE_DIR = "/root/robot_bridge"


ROBOT_CLIENT = r'''#!/usr/bin/env python3
import argparse
import datetime as dt
import json
import os
import urllib.error
import urllib.request


BASE_DIR = "/root/robot_bridge"
CONFIG_FILE = os.path.join(BASE_DIR, "robot_bridge_config.json")
LOG_FILE = os.path.join(BASE_DIR, "robot_commands.jsonl")

DEFAULT_CONFIG = {
    "mode": "mock",
    "controller_url": "http://192.168.43.100:5000/robot_command",
    "timeout": 3,
}

VALID_COMMANDS = {
    "home",
    "stop",
    "open_gripper",
    "close_gripper",
    "pick_water_left",
    "pick_water_right",
    "pick_yogurt_left",
    "pick_yogurt_right",
    "pick_drink_left",
    "pick_drink_right",
}


def ensure_config():
    os.makedirs(BASE_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)


def load_config():
    ensure_config()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    merged = dict(DEFAULT_CONFIG)
    merged.update(cfg)
    return merged


def write_log(payload):
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def send_command(command, item="", target="", source="rdk_voice"):
    if command not in VALID_COMMANDS:
        return {
            "ok": False,
            "mode": "local",
            "message": f"未知机械臂指令：{command}",
        }

    cfg = load_config()
    payload = {
        "command": command,
        "item": item,
        "target": target,
        "source": source,
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
    }
    write_log(payload)

    if cfg.get("mode") != "http":
        return {
            "ok": True,
            "mode": "mock",
            "message": f"模拟发送成功：{command}",
            "payload": payload,
        }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        cfg["controller_url"],
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=float(cfg.get("timeout", 3))) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return {
            "ok": True,
            "mode": "http",
            "status": resp.status,
            "message": body[:300],
            "payload": payload,
        }
    except urllib.error.HTTPError as exc:
        body = exc.read(200).decode("utf-8", errors="replace")
        return {
            "ok": False,
            "mode": "http",
            "message": f"HTTP {exc.code}: {body}",
            "payload": payload,
        }
    except Exception as exc:
        return {
            "ok": False,
            "mode": "http",
            "message": f"{type(exc).__name__}: {exc}",
            "payload": payload,
        }


def command_from_item_side(item, side):
    item_map = {
        "矿泉水": "water",
        "水瓶": "water",
        "酸奶": "yogurt",
        "饮料": "drink",
    }
    side_map = {
        "左边": "left",
        "右边": "right",
    }
    item_key = item_map.get(item, "")
    side_key = side_map.get(side, "")
    if not item_key or not side_key:
        return ""
    return f"pick_{item_key}_{side_key}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="机械臂高层指令，比如 home、stop、pick_water_left")
    parser.add_argument("--item", default="")
    parser.add_argument("--target", default="")
    parser.add_argument("--source", default="manual")
    args = parser.parse_args()

    result = send_command(args.command, item=args.item, target=args.target, source=args.source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


ROBOT_MOCK_SERVER = r'''#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import json


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"raw": raw}

        print("收到机械臂指令：", json.dumps(payload, ensure_ascii=False), flush=True)
        body = json.dumps({"ok": True, "received": payload}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    print("机械臂模拟控制端已启动：http://0.0.0.0:5000/robot_command", flush=True)
    HTTPServer(("0.0.0.0", 5000), Handler).serve_forever()
'''


TEST_SCRIPT = r'''#!/usr/bin/env bash
set -e
python3 /root/robot_bridge/robot_client.py home
python3 /root/robot_bridge/robot_client.py open_gripper
python3 /root/robot_bridge/robot_client.py pick_water_left --item 矿泉水 --target 左边
python3 /root/robot_bridge/robot_client.py stop
echo "robot bridge test done"
'''


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    HOST,
    username=USER,
    password=PASSWORD,
    timeout=8,
    auth_timeout=8,
    look_for_keys=False,
    allow_agent=False,
)

stdin, stdout, stderr = client.exec_command(f"mkdir -p {REMOTE_DIR}", timeout=20)
stdout.channel.recv_exit_status()

sftp = client.open_sftp()
files = {
    f"{REMOTE_DIR}/robot_client.py": ROBOT_CLIENT,
    f"{REMOTE_DIR}/robot_mock_server.py": ROBOT_MOCK_SERVER,
    f"{REMOTE_DIR}/test_robot_bridge.sh": TEST_SCRIPT,
}
for path, content in files.items():
    with sftp.file(path, "w") as f:
        f.write(content)
sftp.close()

cmd = f"""set -e
chmod +x {REMOTE_DIR}/robot_client.py {REMOTE_DIR}/robot_mock_server.py {REMOTE_DIR}/test_robot_bridge.sh
python3 -m py_compile {REMOTE_DIR}/robot_client.py {REMOTE_DIR}/robot_mock_server.py
{REMOTE_DIR}/test_robot_bridge.sh
tail -n 5 {REMOTE_DIR}/robot_commands.jsonl
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=60)
out = stdout.read().decode(errors="replace")
err = stderr.read().decode(errors="replace")
if out:
    print(out)
if err:
    print("ERR:", err)
print("exit", stdout.channel.recv_exit_status())
client.close()
