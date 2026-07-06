import sys

sys.path.insert(0, "pydeps")

import paramiko


client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    "192.168.127.10",
    username="root",
    password="root",
    timeout=8,
    auth_timeout=8,
    look_for_keys=False,
    allow_agent=False,
)

cmd = r"""set -e
photo=$(ls -t /root/voice_photo/photos/*.jpg 2>/dev/null | head -n 1 || true)
echo "latest photo: $photo"
if [ -z "$photo" ]; then
  echo "no photo found"
  exit 2
fi
python3 /root/voice_photo/voice_text_assistant.py --detect-image "$photo"
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
