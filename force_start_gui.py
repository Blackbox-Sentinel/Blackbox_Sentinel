import paramiko
import socket
import sys

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ip = socket.gethostbyname(HOSTNAME)
    client.connect(ip, username=USERNAME, password=PASSWORD, timeout=5)
except Exception as e:
    sys.exit(1)

commands = [
    "systemctl status gui.service | tail -n 10",
    "cat /home/admin/.local/share/xorg/Xorg.0.log | grep -E '(EE|WW)'",
    # Force start X11 on the physical screen (vt1)
    "echo '12345' | sudo -S killall -9 Xorg startx openbox-session xterm",
    "echo '12345' | sudo -S sh -c 'nohup startx /home/admin/.xinitrc -- /usr/bin/X :0 vt1 -nocursor >/dev/null 2>&1 &'"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        for line in iter(stdout.readline, ""):
            print("   " + line.strip('\n').encode('ascii', 'ignore').decode('ascii'))
    except Exception:
        pass

client.close()
