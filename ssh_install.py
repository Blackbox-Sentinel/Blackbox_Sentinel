import paramiko
import time
import sys

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

print("[*] Connecting to Pi to manually inject modern drivers...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
    print("[+] SSH Connected!")
except Exception as e:
    print(f"[-] SSH connection failed: {e}")
    sys.exit(1)

# 1. Download the driver to the correct Bookworm folder
commands = [
    # Bookworm uses /boot/firmware
    "echo '12345' | sudo -S wget -qO /boot/firmware/overlays/tft35a.dtbo https://raw.githubusercontent.com/goodtft/LCD-show/master/usr/tft35a.dtbo",
    
    # Enable SPI and load the driver
    "echo '12345' | sudo -S sh -c 'echo \"dtparam=spi=on\" >> /boot/firmware/config.txt'",
    "echo '12345' | sudo -S sh -c 'echo \"dtoverlay=tft35a:rotate=90\" >> /boot/firmware/config.txt'",
    
    # Route console to screen
    "echo '12345' | sudo -S sed -i '1 s/$/ fbcon=map:10 fbcon=font:ProFont6x11/' /boot/firmware/cmdline.txt",
    
    # Reboot
    "echo '12345' | sudo -S reboot"
]

for cmd in commands:
    print(f"[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()

print("[+] Manual injection complete! The Pi is rebooting.")
client.close()
