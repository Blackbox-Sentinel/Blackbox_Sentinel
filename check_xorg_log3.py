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
    "cat /home/admin/.local/share/xorg/Xorg.0.log | tail -n 25",
    "cat /var/log/Xorg.0.log | tail -n 25"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        output = stdout.read().decode('utf-8', errors='replace')
        print(output)
    except Exception as e:
        pass

client.close()
