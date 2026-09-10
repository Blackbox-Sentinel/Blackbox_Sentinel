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

service_file = """[Unit]
Description=Sentinel Kiosk UI
After=systemd-user-sessions.service

[Service]
User=admin
Environment=DISPLAY=:0
ExecStart=/usr/bin/startx /home/admin/.xinitrc -- /usr/bin/X :0 vt1 -nocursor
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

print("[*] Creating systemd service...")
client.exec_command(f"echo \"{service_file}\" > /home/admin/sentinel-kiosk.service")
client.exec_command("echo '12345' | sudo -S mv /home/admin/sentinel-kiosk.service /etc/systemd/system/sentinel-kiosk.service")
client.exec_command("echo '12345' | sudo -S systemctl daemon-reload")
client.exec_command("echo '12345' | sudo -S systemctl enable sentinel-kiosk.service")

print("[*] Cleaning up .bash_profile auto-start hack...")
client.exec_command("rm -f /home/admin/.bash_profile")

client.close()
