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
    # Kill the hanging upower and dpkg processes!
    "echo '12345' | sudo -S killall -9 dpkg upower upowerd apt-get",
    
    # Force complete the installation of chromium directly
    "echo '12345' | sudo -S rm /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock",
    "echo '12345' | sudo -S apt-get install -y chromium-browser openbox unclutter x11-xserver-utils",
    
    # Restart the kiosk
    "echo '12345' | sudo -S systemctl restart kiosk.service"
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
