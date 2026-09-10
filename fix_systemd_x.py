import paramiko
import socket
import sys
import time

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

print("[*] Fixing Xwrapper.config...")
client.exec_command("echo '12345' | sudo -S sh -c 'echo \"allowed_users=anybody\" > /etc/X11/Xwrapper.config'")

print("[*] Updating systemd service...")
client.exec_command(f"echo \"{service_file}\" > /home/admin/sentinel-kiosk.service")
client.exec_command("echo '12345' | sudo -S mv /home/admin/sentinel-kiosk.service /etc/systemd/system/sentinel-kiosk.service")
client.exec_command("echo '12345' | sudo -S systemctl daemon-reload")

print("[*] Stopping old processes...")
client.exec_command("echo '12345' | sudo -S systemctl stop sentinel-kiosk.service")
client.exec_command("echo '12345' | sudo -S killall -9 X Xorg.wrap xinit startx python3 openbox")
time.sleep(2)

print("[*] Starting service...")
client.exec_command("echo '12345' | sudo -S systemctl start sentinel-kiosk.service")
time.sleep(3)

print("[*] Checking status...")
stdin, stdout, stderr = client.exec_command("sudo systemctl status sentinel-kiosk.service -n 20")
for line in iter(stdout.readline, ""):
    print("   " + line.strip('\n'))

client.close()
