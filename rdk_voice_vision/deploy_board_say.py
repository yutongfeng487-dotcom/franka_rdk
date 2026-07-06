import posixpath
import sys

sys.path.insert(0, "pydeps")

import paramiko


HOST = "192.168.127.10"
USER = "root"
PASSWORD = "root"

REMOTE_DIR = "/root/voice_photo"
REMOTE_SCRIPT = posixpath.join(REMOTE_DIR, "say.py")


SAY_SCRIPT = r'''#!/usr/bin/env python3
import asyncio
import os
import subprocess
import sys

import edge_tts


BASE_DIR = "/root/voice_photo"
MP3_FILE = os.path.join(BASE_DIR, "tts_output.mp3")
WAV_FILE = os.path.join(BASE_DIR, "tts_output.wav")
VOICE = "zh-CN-XiaoxiaoNeural"
PLAY_DEVICE = "plughw:CARD=duplexaudio,DEV=0"


async def synthesize(text):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(MP3_FILE)


def speak(text):
    os.makedirs(BASE_DIR, exist_ok=True)
    asyncio.run(synthesize(text))
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", MP3_FILE, "-ar", "16000", "-ac", "1", WAV_FILE],
        check=True,
    )
    subprocess.run(["aplay", "-D", PLAY_DEVICE, WAV_FILE], check=True)


def main():
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        text = "你好，我是 RDK X5 开发板。"
    speak(text)


if __name__ == "__main__":
    main()
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
with sftp.file(REMOTE_SCRIPT, "w") as remote_file:
    remote_file.write(SAY_SCRIPT)
sftp.close()

cmd = f"""set -e
chmod +x {REMOTE_SCRIPT}
python3 -m py_compile {REMOTE_SCRIPT}
python3 {REMOTE_SCRIPT} '你好，我是 R D K X 五开发板，现在可以通过代码说话。'
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
