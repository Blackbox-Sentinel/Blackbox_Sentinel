import paramiko
import time
import socket
import sys

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

print("[*] Reconnecting to live-test SPI drivers...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ip = socket.gethostbyname(HOSTNAME)
    client.connect(ip, username=USERNAME, password=PASSWORD, timeout=10)
    print("[+] SSH Connected!")
except Exception as e:
    print(f"[-] SSH failed: {e}")
    sys.exit(1)

commands = [
    # Remove the broken overlay from config.txt
    "echo '12345' | sudo -S sed -i '/tft35a/d' /boot/firmware/config.txt",
    "echo '12345' | sudo -S sed -i '/piscreen/d' /boot/firmware/config.txt",
    
    # Try loading the generic flexfb driver for ili9486 live!
    "echo '12345' | sudo -S modprobe spi-bcm2835",
    "echo '12345' | sudo -S modprobe fbtft_device custom name=fb_ili9486 gpios=reset:25,dc:24,cs:8,led:18 speed=16000000 rotate=90 bgr=1",
    "echo '12345' | sudo -S modprobe fbtft_device name=piscreen speed=16000000 rotate=90",
    "echo '12345' | sudo -S modprobe fbtft_device name=waveshare32b speed=16000000 rotate=90",
    
    # Check if fb1 was created
    "ls -l /dev/fb*"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    for line in iter(stdout.readline, ""):
        print("   " + line.strip())
        
client.close()
