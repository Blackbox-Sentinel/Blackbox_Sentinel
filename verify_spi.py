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
    client.connect(ip, username=USERNAME, password=PASSWORD, timeout=10)
    print("[+] SSH Connected!")
except Exception as e:
    print(f"[-] SSH failed: {e}")
    sys.exit(1)

commands = [
    "cat /boot/firmware/config.txt | tail -n 25",
    "ls -l /dev/fb*",
    "ps aux | grep fbcp",
    "dmesg | grep spi",
    "lsmod | grep spi"
]

for cmd in commands:
    print(f"\n[*] Output of {cmd}:")
    stdin, stdout, stderr = client.exec_command(cmd)
    for line in iter(stdout.readline, ""):
        print("   " + line.strip())

client.close()
