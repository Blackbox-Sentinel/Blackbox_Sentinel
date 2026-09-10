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
After=systemd-user-sessions.service plymouth-quit-wait.service
Conflicts=getty@tty1.service

[Service]
User=admin
Environment=DISPLAY=:0
Environment=FRAMEBUFFER=/dev/fb1
ExecStart=/usr/bin/startx /home/admin/.xinitrc -- /usr/bin/X :0 vt1 -nocursor -s 0 -dpms
Restart=always
RestartSec=5
StandardInput=tty
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes

[Install]
WantedBy=graphical.target
"""

print("[*] Removing bad xorg.conf.d file...")
client.exec_command("echo '12345' | sudo -S rm -f /usr/share/X11/xorg.conf.d/99-spi-display.conf /etc/X11/xorg.conf.d/99-fbdev.conf")

print("[*] Updating systemd service with FRAMEBUFFER env...")
client.exec_command(f"echo \"{service_file}\" > /home/admin/sentinel-kiosk.service")
client.exec_command("echo '12345' | sudo -S mv /home/admin/sentinel-kiosk.service /etc/systemd/system/sentinel-kiosk.service")
client.exec_command("echo '12345' | sudo -S systemctl daemon-reload")

print("[*] Restarting Sentinel Kiosk Service...")
client.exec_command("echo '12345' | sudo -S systemctl restart sentinel-kiosk.service")

import time
time.sleep(3)
print("[*] Logs:")
stdin, stdout, stderr = client.exec_command("sudo journalctl -u sentinel-kiosk.service -n 20 --no-pager")
for line in iter(stdout.readline, ""):
    print("   " + line.strip('\n'))

client.close()
