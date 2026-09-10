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
    # Check if apt/dpkg is hanging
    "ps aux | grep -E 'apt|dpkg'",
    # Force kill them just in case
    "echo '12345' | sudo -S killall -9 apt apt-get dpkg",
    # Remove lock files
    "echo '12345' | sudo -S rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock",
    # Re-configure forcefully
    "echo '12345' | sudo -S DEBIAN_FRONTEND=noninteractive dpkg --configure -a",
    # Verify xinit exists
    "which startx",
    # Run startx on the physical console
    "echo '12345' | sudo -S sh -c 'nohup startx /home/admin/.xinitrc -- /usr/bin/X :0 vt1 -nocursor >/tmp/startx.log 2>&1 &'",
    "sleep 2",
    "cat /tmp/startx.log"
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
