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

conf = """Section "Device"
  Identifier "SPI Display"
  Driver "fbdev"
  Option "fbdev" "/dev/fb1"
EndSection

Section "Screen"
  Identifier "SPI Screen"
  Device "SPI Display"
  DefaultDepth 16
EndSection

Section "ServerLayout"
  Identifier "Default Layout"
  Screen 0 "SPI Screen" 0 0
EndSection
"""

print("[*] Deploying full X11 SPI configuration...")
client.exec_command("echo '12345' | sudo -S rm -f /usr/share/X11/xorg.conf.d/99-fbdev.conf /etc/X11/xorg.conf.d/99-fbdev.conf /usr/share/X11/xorg.conf.d/99-spi-display.conf")
client.exec_command(f"echo '{conf}' | sudo -S tee /etc/X11/xorg.conf.d/99-spi-display.conf")

print("[*] Restarting Sentinel Kiosk Service...")
client.exec_command("echo '12345' | sudo -S systemctl restart sentinel-kiosk.service")

import time
time.sleep(3)

print("[*] Xorg processes:")
stdin, stdout, stderr = client.exec_command("ps aux | grep -E 'python|X|startx'")
for line in iter(stdout.readline, ""):
    print("   " + line.strip('\n'))

print("[*] Checking Xorg Log:")
stdin, stdout, stderr = client.exec_command("cat /home/admin/.local/share/xorg/Xorg.0.log | tail -n 15")
for line in iter(stdout.readline, ""):
    print("   " + line.strip('\n'))
stdin, stdout, stderr = client.exec_command("cat /var/log/Xorg.0.log | tail -n 15")
for line in iter(stdout.readline, ""):
    print("   " + line.strip('\n'))

client.close()
