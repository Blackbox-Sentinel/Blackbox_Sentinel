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
    "cat /boot/firmware/config.txt | grep -i vc4",
    "cat /boot/config.txt | grep -i vc4",
    "ls -l /dev/dri"
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
