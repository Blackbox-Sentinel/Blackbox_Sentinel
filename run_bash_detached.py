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

# Execute it detached using bash explicitly to avoid permission denied
client.exec_command("echo '12345' | sudo -S nohup bash /home/admin/install.sh >/home/admin/install.log 2>&1 &")

client.close()
