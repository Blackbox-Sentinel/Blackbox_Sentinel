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

print("[*] Disabling vc4 DRM driver in config.txt...")
client.exec_command("echo '12345' | sudo -S sed -i 's/dtoverlay=vc4-kms-v3d/#dtoverlay=vc4-kms-v3d/' /boot/firmware/config.txt")
client.exec_command("echo '12345' | sudo -S sed -i 's/dtoverlay=vc4-fkms-v3d/#dtoverlay=vc4-fkms-v3d/' /boot/firmware/config.txt")

print("[*] Rebooting the Raspberry Pi...")
client.exec_command("echo '12345' | sudo -S reboot")

client.close()
print("[*] Reboot command sent successfully.")
