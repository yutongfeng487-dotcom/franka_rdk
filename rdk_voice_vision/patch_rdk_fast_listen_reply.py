import re
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

# Make listening more responsive: shorter chunks instead of waiting 5 seconds.
text = text.replace("def record_audio(seconds=5):", "def record_audio(seconds=2):")
text = text.replace("record_audio(5)", "record_audio(2)")
text = text.replace("开始录音 5 秒，请说话...", "开始录音 2 秒，请说话...")

# Wait for speech playback before listening again, so the mic does not capture its own reply.
old = '''    try:
        subprocess.Popen(
            ["python3", SAY_SCRIPT, text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
'''

new = '''    try:
        subprocess.run(
            ["python3", SAY_SCRIPT, text],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
'''

if old in text:
    text = text.replace(old, new)
else:
    raise RuntimeError("reply playback block not found")

# Keep complex fallback from feeling too slow.
text = text.replace('"max_tokens": 120,', '"max_tokens": 70,')
text = text.replace("urllib.request.urlopen(req, timeout=12)", "urllib.request.urlopen(req, timeout=8)")

with sftp.file(REMOTE_SCRIPT, "w") as f:
    f.write(text)
sftp.close()

cmd = f"""set -e
python3 -m py_compile {REMOTE_SCRIPT}
systemctl restart voice-vision-assistant.service
sleep 6
systemctl --no-pager --full status voice-vision-assistant.service || true
journalctl -u voice-vision-assistant -n 25 --no-pager || true
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=100)
out = stdout.read().decode(errors="replace")
err = stderr.read().decode(errors="replace")
if out:
    print(out)
if err:
    print("ERR:", err)
print("exit", stdout.channel.recv_exit_status())
client.close()
