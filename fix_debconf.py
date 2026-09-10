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

print("[*] Fixing Debconf Database...")
client.exec_command("echo '12345' | sudo -S rm -f /var/cache/debconf/*.dat")
client.exec_command("echo '12345' | sudo -S dpkg-reconfigure -f noninteractive debconf")

print("[*] Running dpkg --configure -a again")
stdin, stdout, stderr = client.exec_command("echo '12345' | sudo -S dpkg --configure -a")
for line in iter(stdout.readline, ""):
    pass

print("[*] Rerunning apt-get install openbox")
stdin, stdout, stderr = client.exec_command("echo '12345' | sudo -S DEBIAN_FRONTEND=noninteractive apt-get install -y --fix-missing openbox python3-tk x11-xserver-utils")
for line in iter(stdout.readline, ""):
    pass

print("[*] Launching X...")
client.exec_command("echo '12345' | sudo -S sh -c 'nohup startx /home/admin/.xinitrc -- /usr/bin/X :0 vt1 -nocursor >/tmp/startx.log 2>&1 &'")

time.sleep(3)

print("[*] startx.log output:")
stdin, stdout, stderr = client.exec_command("cat /tmp/startx.log")
for line in iter(stdout.readline, ""):
    print("   " + line.strip('\n'))

client.close()
