import sys

sys.path.insert(0, "pydeps")

import paramiko


def run(client, command, timeout=30):
    print(f"\n### {command}")
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    code = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err:
        print("ERR:", err)
    print(f"[exit {code}]")


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

commands = [
    "hostname; date",
    "lsusb",
    "cat /proc/asound/cards 2>/dev/null || true",
    "arecord -l 2>/dev/null || true",
    "arecord -L 2>/dev/null | sed -n '1,120p' || true",
]

for cmd in commands:
    run(client, cmd)

client.close()
