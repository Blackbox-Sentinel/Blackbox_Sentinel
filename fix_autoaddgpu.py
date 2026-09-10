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

conf = """Section "ServerFlags"
  Option "AutoAddGPU" "off"
EndSection

Section "Device"
  Identifier "SPI Display"
  Driver "fbdev"
  Option "fbdev" "/dev/fb1"
EndSection

Section "Monitor"
  Identifier "SPI Monitor"
EndSection

Section "Screen"
  Identifier "Default Screen"
  Device "SPI Display"
  Monitor "SPI Monitor"
  DefaultDepth 16
EndSection

Section "ServerLayout"
  Identifier "Default Layout"
  Screen 0 "Default Screen"
EndSection
"""

print("[*] Deploying ultimate X11 SPI configuration...")
client.exec_command(f"echo '{conf}' | sudo -S tee /usr/share/X11/xorg.conf.d/99-spi-display.conf")

print("[*] Restarting Sentinel Kiosk Service...")
client.exec_command("echo '12345' | sudo -S systemctl restart sentinel-kiosk.service")

time.sleep(3)
print("[*] Checking Xorg Log...")
stdin, stdout, stderr = client.exec_command("cat /home/admin/.local/share/xorg/Xorg.0.log | tail -n 25")
for line in iter(stdout.readline, ""):
    print("   " + line.strip('\n'))

client.close()
