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
except Exception:
    sys.exit(1)

print("[*] Killing old X processes...")
client.exec_command("echo '12345' | sudo -S killall -9 Xorg xinit startx python3 openbox")
import time
time.sleep(2)

print("[*] Restarting Sentinel Kiosk Service...")
client.exec_command("echo '12345' | sudo -S systemctl restart sentinel-kiosk.service")

time.sleep(3)
print("[*] Current running python processes:")
stdin, stdout, stderr = client.exec_command("ps aux | grep python")
for line in iter(stdout.readline, ""):
    print("   " + line.strip('\n'))

client.close()
