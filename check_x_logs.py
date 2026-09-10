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
    "sudo journalctl -u sentinel-kiosk.service -n 50",
    "cat /home/admin/.local/share/xorg/Xorg.0.log | tail -n 20",
    "cat /var/log/Xorg.0.log | tail -n 20"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(f"echo '12345' | sudo -S {cmd}")
    try:
        for line in iter(stdout.readline, ""):
            print("   " + line.strip('\n'))
    except Exception:
        pass

client.close()
