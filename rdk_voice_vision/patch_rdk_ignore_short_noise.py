import sys

sys.path.insert(0, "pydeps")

import paramiko


HOST = "192.168.127.10"
USER = "root"
PASSWORD = "root"
REMOTE_SCRIPT = "/root/voice_photo/voice_vision_daemon.py"


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

sftp = client.open_sftp()
with sftp.file(REMOTE_SCRIPT, "r") as f:
    text = f.read().decode("utf-8")

marker = '''    log("你说：" + text)

    if state.get("pending_flip"):
'''
replacement = '''    log("你说：" + text)

    if len(text) <= 1 and text not in ["好", "是", "要", "开", "关"]:
        return True

    if state.get("pending_flip"):
'''

if marker not in text:
    raise RuntimeError("insert marker not found")
text = text.replace(marker, replacement, 1)

with sftp.file(REMOTE_SCRIPT, "w") as f:
    f.write(text)
sftp.close()

cmd = f"""set -e
python3 -m py_compile {REMOTE_SCRIPT}
systemctl restart voice-vision-assistant.service
sleep 5
systemctl --no-pager --full status voice-vision-assistant.service || true
journalctl -u voice-vision-assistant -n 20 --no-pager || true
"""
stdin, stdout, stderr = client.exec_command(cmd, timeout=90)
out = stdout.read().decode(errors="replace")
err = stderr.read().decode(errors="replace")
if out:
    print(out)
if err:
    print("ERR:", err)
print("exit", stdout.channel.recv_exit_status())
client.close()
