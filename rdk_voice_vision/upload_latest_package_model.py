import os
import posixpath
import sys

sys.path.insert(0, "pydeps")

import paramiko


HOST = "192.168.127.10"
USER = "root"
PASSWORD = "root"
LOCAL_ONNX = r"E:\rdk_package_dataset\runs\package_sort_v1-2\weights\best.onnx"
REMOTE_DIR = "/root/voice_photo/vision_models"
REMOTE_ONNX = posixpath.join(REMOTE_DIR, "package_sort_best.onnx")
REMOTE_BACKUP = posixpath.join(REMOTE_DIR, "package_sort_best.previous.onnx")


if not os.path.exists(LOCAL_ONNX):
    raise FileNotFoundError(LOCAL_ONNX)

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

cmd = f"""set -e
mkdir -p {REMOTE_DIR}
if [ -f {REMOTE_ONNX} ]; then cp {REMOTE_ONNX} {REMOTE_BACKUP}; fi
systemctl stop voice-vision-assistant.service || true
"""
stdin, stdout, stderr = client.exec_command(cmd, timeout=30)
stdout.channel.recv_exit_status()

sftp = client.open_sftp()
print(f"upload {LOCAL_ONNX} -> {REMOTE_ONNX}")
sftp.put(LOCAL_ONNX, REMOTE_ONNX)
sftp.close()

cmd = f"""set -e
ls -lh {REMOTE_ONNX} {REMOTE_BACKUP} 2>/dev/null || true
systemctl start voice-vision-assistant.service
sleep 8
systemctl --no-pager --full status voice-vision-assistant.service || true
journalctl -u voice-vision-assistant -n 30 --no-pager || true
"""
stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
out = stdout.read().decode(errors="replace")
err = stderr.read().decode(errors="replace")
if out:
    print(out)
if err:
    print("ERR:", err)
print("exit", stdout.channel.recv_exit_status())
client.close()
