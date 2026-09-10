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

# FORCE kill absolutely everything
client.exec_command("echo '12345' | sudo -S killall -9 dpkg apt apt-get dpkg-deb")
client.exec_command("echo '12345' | sudo -S rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock")

# Run dpkg configure synchronously here since it doesn't drop the connection usually
print("[*] Running dpkg --configure -a")
stdin, stdout, stderr = client.exec_command("echo '12345' | sudo -S dpkg --configure -a")
for line in iter(stdout.readline, ""):
    pass

print("[*] Installing openbox and dependencies")
# Run openbox install
stdin, stdout, stderr = client.exec_command("echo '12345' | sudo -S DEBIAN_FRONTEND=noninteractive apt-get install -y --fix-missing openbox python3-tk x11-xserver-utils")
for line in iter(stdout.readline, ""):
    print(line.strip())

client.close()
