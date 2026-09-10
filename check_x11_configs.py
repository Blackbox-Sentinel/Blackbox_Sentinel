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
    "ls -l /usr/share/X11/xorg.conf.d/",
    "cat /usr/share/X11/xorg.conf.d/99-fbturbo.conf 2>/dev/null",
    "cat /usr/share/X11/xorg.conf.d/99-fbdev.conf 2>/dev/null",
    "cat /usr/share/X11/xorg.conf.d/99-calibration.conf 2>/dev/null"
]

for cmd in commands:
    print(f"\n[*] Output of {cmd}:")
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        for line in iter(stdout.readline, ""):
            print("   " + line.strip('\n').encode('ascii', 'ignore').decode('ascii'))
    except Exception:
        pass

client.close()
