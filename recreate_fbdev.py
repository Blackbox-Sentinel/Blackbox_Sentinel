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

conf = """Section "Device"
  Identifier "SPI"
  Driver "fbdev"
  Option "fbdev" "/dev/fb1"
EndSection
"""

print("[*] Recreating simple 99-fbdev.conf...")
client.exec_command(f"echo '{conf}' | sudo -S tee /usr/share/X11/xorg.conf.d/99-fbdev.conf")

print("[*] Restarting Sentinel Kiosk Service...")
client.exec_command("echo '12345' | sudo -S systemctl restart sentinel-kiosk.service")

time.sleep(3)
print("[*] Checking Xorg Log...")
stdin, stdout, stderr = client.exec_command("cat /var/log/Xorg.0.log | grep -i fb1")
for line in iter(stdout.readline, ""):
    print("   " + line.strip('\n'))

client.close()
