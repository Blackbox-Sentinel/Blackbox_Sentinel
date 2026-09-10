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
    print("[*] SSH connection successful! The Pi is fully booted!")
except Exception as e:
    print(f"[*] SSH connection failed: {e}")
    sys.exit(1)

commands = [
    # Force finish the package manager installation!
    "echo '12345' | sudo -S rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock",
    "echo '12345' | sudo -S sh -c 'DEBIAN_FRONTEND=noninteractive dpkg --configure -a --force-confdef --force-confold'",
    "echo '12345' | sudo -S sh -c 'DEBIAN_FRONTEND=noninteractive apt-get install -f -y'",
    
    # Check if chromium is finally there
    "which chromium-browser",
    
    # Restart the kiosk to pull up the screen!
    "echo '12345' | sudo -S systemctl restart kiosk.service"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        for line in iter(stdout.readline, ""):
            pass # ignore output to avoid blocking
    except Exception:
        pass

print("[*] Recovery script deployed!")
client.close()
