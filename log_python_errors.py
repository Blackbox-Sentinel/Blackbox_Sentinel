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

xinitrc_content = """#!/bin/bash
xset s off
xset -dpms
xset s noblank

openbox-session &
python3 /home/admin/kiosk_ui.py > /tmp/kiosk.log 2>&1
# keep xinit running even if python crashes
sleep 3600
"""

client.exec_command(f"echo \"{xinitrc_content}\" > /home/admin/.xinitrc")

client.close()
