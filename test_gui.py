import paramiko
import socket
import sys
import time

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("[*] Waiting for Raspberry Pi to boot up...")
while True:
    try:
        ip = socket.gethostbyname(HOSTNAME)
        client.connect(ip, username=USERNAME, password=PASSWORD, timeout=5)
        print("[*] Connected! Deploying graphics test...")
        break
    except Exception:
        time.sleep(3)

commands = [
    # Stop the automated kiosk service from interfering
    "echo '12345' | sudo -S systemctl stop kiosk.service",
    "echo '12345' | sudo -S killall -9 Xorg startx",
    
    # Overwrite the broken .xinitrc with an empty one so it defaults to the X11 pattern
    "echo '' > /home/admin/.xinitrc",
    
    # Force X11 to start completely barebones! It will show a black/white patterned background and a mouse cursor.
    "echo '12345' | sudo -S nohup startx -- -nocursor >/dev/null 2>&1 &"
]

for cmd in commands:
    print(f"[*] Executing: {cmd}")
    client.exec_command(cmd)

print("[*] Graphics deployed! Look at the screen!")
client.close()
