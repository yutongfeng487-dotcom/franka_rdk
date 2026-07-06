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
python3 - <<'PY'
import wave, math, struct
path = "/tmp/rdk_speaker_test.wav"
rate = 16000
seconds = 2
freq = 880
with wave.open(path, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(rate)
    for i in range(rate * seconds):
        v = int(14000 * math.sin(2 * math.pi * freq * i / rate))
        wf.writeframes(struct.pack("<h", v))
print(path)
PY
echo "== mixer controls =="
amixer -c 2 scontrols || true
amixer -c 2 scontents | head -n 120 || true
echo
echo "== explicit playback =="
aplay -D plughw:CARD=duplexaudio,DEV=0 /tmp/rdk_speaker_test.wav
"""

stdin, stdout, stderr = client.exec_command(cmd, timeout=80)
print(stdout.read().decode(errors="replace"))
err = stderr.read().decode(errors="replace")
if err:
    print("ERR:", err)
print("exit", stdout.channel.recv_exit_status())
client.close()
