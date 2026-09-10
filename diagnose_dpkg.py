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

# Just run dpkg --configure -a to see the real root error
cmd = "echo '12345' | sudo -S dpkg --configure x11-common"

print(f"\n[*] Executing: {cmd}")
stdin, stdout, stderr = client.exec_command(cmd)
try:
    for line in iter(stdout.readline, ""):
        print("   " + line.strip('\n'))
except Exception:
    pass
    
cmd = "echo '12345' | sudo -S dpkg --configure libpaper1:armhf"
print(f"\n[*] Executing: {cmd}")
stdin, stdout, stderr = client.exec_command(cmd)
try:
    for line in iter(stdout.readline, ""):
        print("   " + line.strip('\n'))
except Exception:
    pass

client.close()
