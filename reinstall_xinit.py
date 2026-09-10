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
except Exception:
    sys.exit(1)

commands = [
    "echo '12345' | sudo -S apt-get update",
    "echo '12345' | sudo -S apt-get install -y xinit xserver-xorg-legacy",
    "which startx",
    "ls -l /usr/bin/startx"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        for line in iter(stdout.readline, ""):
            print("   " + line.strip('\n'))
    except Exception:
        pass
    try:
        for line in iter(stderr.readline, ""):
            print("   ERR: " + line.strip('\n'))
    except Exception:
        pass

client.close()
