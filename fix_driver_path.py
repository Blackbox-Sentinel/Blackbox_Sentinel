import paramiko
import time
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
    # The GoodTFT script copied the driver hardware binaries to the old Bullseye folder.
    # We must move them to the modern Bookworm firmware folder so the GPU can load them!
    "echo '12345' | sudo -S cp -r /boot/overlays/tft* /boot/firmware/overlays/ 2>/dev/null",
    
    # Let's also grab them from the LCD-show folder just in case
    "cd LCD-show && echo '12345' | sudo -S cp ./usr/tft35a-overlay.dtb /boot/firmware/overlays/tft35a.dtbo",
    "cd LCD-show && echo '12345' | sudo -S cp ./usr/tft35a-overlay.dtb /boot/firmware/overlays/tft35a-overlay.dtbo",
    
    # Ensure fbcp runs in the background at boot
    "echo '12345' | sudo -S sh -c 'grep -q \"fbcp\" /etc/rc.local || sed -i \"s/^exit 0/fbcp \\&\\nexit 0/\" /etc/rc.local'",
    
    "echo '12345' | sudo -S reboot -f"
]

for cmd in commands:
    client.exec_command(cmd)

client.close()
