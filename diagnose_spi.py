import paramiko
import time
import socket
import sys

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

print("[*] Reconnecting to diagnose SPI screen...")

while True:
    try:
        ip = socket.gethostbyname(HOSTNAME)
        break
    except socket.gaierror:
        time.sleep(2)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(ip, username=USERNAME, password=PASSWORD, timeout=10)
    print("[+] SSH Connected!")
except Exception as e:
    print(f"[-] SSH failed: {e}")
    sys.exit(1)

commands = [
    "cat /boot/firmware/config.txt | tail -n 20",
    "dmesg | grep -i spi",
    "lsmod | grep fbtft",
    "dmesg | grep -i fb1",
    "ls -l /dev/fb*"
]

for cmd in commands:
    print(f"\n[*] Output of {cmd}:")
    stdin, stdout, stderr = client.exec_command(cmd)
    for line in iter(stdout.readline, ""):
        print("   " + line.strip())

client.close()
