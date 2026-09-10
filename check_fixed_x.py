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
    "ps aux | grep -E 'python|X|startx'",
    "sudo systemctl status sentinel-kiosk.service -n 20 --no-pager"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        output = stdout.read().decode('utf-8', errors='replace')
        print(output)
    except Exception as e:
        print(f"Error reading: {e}")

client.close()
