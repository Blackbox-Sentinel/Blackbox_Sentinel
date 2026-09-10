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
    # Install the missing xinit command
    "echo '12345' | sudo -S apt-get install -y xinit",
    
    # Restart the kiosk
    "echo '12345' | sudo -S systemctl restart kiosk.service"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    client.exec_command(cmd)

client.close()
