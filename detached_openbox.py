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

# Kill hanging apt
client.exec_command("echo '12345' | sudo -S killall -9 apt apt-get dpkg")
client.exec_command("echo '12345' | sudo -S rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock")
client.exec_command("echo '12345' | sudo -S dpkg --configure -a")

script = """#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --fix-missing openbox python3-tk x11-xserver-utils
"""
client.exec_command(f"echo \"{script}\" > /home/admin/install2.sh")
client.exec_command("chmod +x /home/admin/install2.sh")

# Execute detached
client.exec_command("echo '12345' | sudo -S bash /home/admin/install2.sh >/home/admin/install2.log 2>&1 &")

client.close()
