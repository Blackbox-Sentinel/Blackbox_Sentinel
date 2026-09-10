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

commands = [
    # Force fix apt locks and dpkg just to be extremely safe
    "echo '12345' | sudo -S rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock",
    "echo '12345' | sudo -S DEBIAN_FRONTEND=noninteractive dpkg --configure -a",
    # Install xinit directly
    "echo '12345' | sudo -S apt-get install -y --fix-missing xinit xserver-xorg-legacy",
    "which startx",
    "ls -l /usr/bin/startx",
    # Finally run it
    "echo '12345' | sudo -S sh -c 'nohup startx /home/admin/.xinitrc -- /usr/bin/X :0 vt1 -nocursor >/tmp/startx.log 2>&1 &'"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        for line in iter(stdout.readline, ""):
            print("   " + line.strip('\n'))
    except Exception:
        pass

client.close()
