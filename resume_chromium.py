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
except Exception as e:
    sys.exit(1)

commands = [
    # Remove any broken locks from the hard reboot
    "echo '12345' | sudo -S rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock",
    
    # Fix the interrupted dpkg state
    "echo '12345' | sudo -S sh -c 'DEBIAN_FRONTEND=noninteractive dpkg --configure -a --force-confdef --force-confold'",
    "echo '12345' | sudo -S sh -c 'DEBIAN_FRONTEND=noninteractive apt-get install -f -y'",
    
    # Re-trigger the browser installation (it will skip what is already unpacked)
    "echo '12345' | sudo -S apt-get install -y chromium-browser openbox unclutter x11-xserver-utils",
    
    # Restart the graphics engine!
    "echo '12345' | sudo -S systemctl restart kiosk.service",
    "sleep 2",
    "systemctl status kiosk.service -l --no-pager"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        for line in iter(stdout.readline, ""):
            print("   " + line.strip('\n').encode('ascii', 'ignore').decode('ascii'))
    except Exception:
        pass

client.close()
