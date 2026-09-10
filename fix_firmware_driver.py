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
except Exception as e:
    sys.exit(1)

commands = [
    # 1. Properly download the driver
    "echo '12345' | sudo -S curl -L https://github.com/goodtft/LCD-show/raw/master/usr/tft35a-overlay.dtb -o tft35a.dtbo",
    "echo '12345' | sudo -S mv tft35a.dtbo /boot/firmware/overlays/tft35a.dtbo",
    
    # 2. Add config to the correct firmware file
    "echo '12345' | sudo -S sh -c 'echo \"hdmi_force_hotplug=1\" >> /boot/firmware/config.txt'",
    "echo '12345' | sudo -S sh -c 'echo \"dtparam=spi=on\" >> /boot/firmware/config.txt'",
    "echo '12345' | sudo -S sh -c 'echo \"dtoverlay=tft35a:rotate=90\" >> /boot/firmware/config.txt'",
    
    # 3. Reboot to apply!
    "echo '12345' | sudo -S reboot -f"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    client.exec_command(cmd)

client.close()
