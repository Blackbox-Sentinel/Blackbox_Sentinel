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
    # The manufacturer script wrote the driver to the old /boot/ folder. 
    # Bookworm requires it in /boot/firmware/. Let's forcefully copy the patched files to the right place.
    "echo '12345' | sudo -S cp /boot/config.txt /boot/firmware/config.txt",
    
    # Let's ensure fbcp runs on boot by injecting it into rc.local if missing
    "echo '12345' | sudo -S sed -i 's/^exit 0/fbcp \\&\\nexit 0/' /etc/rc.local",
    
    # Route console output to the secondary framebuffer
    "echo '12345' | sudo -S sed -i '1 s/$/ fbcon=map:10 fbcon=font:ProFont6x11/' /boot/firmware/cmdline.txt",
    
    "echo '12345' | sudo -S reboot -f"
]

for cmd in commands:
    client.exec_command(cmd)

client.close()
