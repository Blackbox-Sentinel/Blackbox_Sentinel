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

fbdev_conf = """Section "Device"
  Identifier "SPI Display"
  Driver "fbdev"
  Option "fbdev" "/dev/fb1"
EndSection
"""

print("[*] Creating Xorg fbdev configuration for /dev/fb1...")
client.exec_command("echo '12345' | sudo -S mkdir -p /etc/X11/xorg.conf.d/")
client.exec_command(f"echo '{fbdev_conf}' | sudo -S tee /etc/X11/xorg.conf.d/99-fbdev.conf")

print("[*] Installing xserver-xorg-video-fbdev just in case...")
stdin, stdout, stderr = client.exec_command("echo '12345' | sudo -S DEBIAN_FRONTEND=noninteractive apt-get install -y xserver-xorg-video-fbdev")
stdout.channel.recv_exit_status()

print("[*] Restarting Sentinel Kiosk Service...")
client.exec_command("echo '12345' | sudo -S systemctl restart sentinel-kiosk.service")

import time
time.sleep(3)

print("[*] Checking Xorg logs for fb1 usage:")
stdin, stdout, stderr = client.exec_command("cat /var/log/Xorg.0.log | grep fb1")
for line in iter(stdout.readline, ""):
    print("   " + line.strip('\n'))

client.close()
