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
    # Allow X11 to be run by the kiosk service
    "echo '12345' | sudo -S sh -c 'echo \"allowed_users=anybody\" > /etc/X11/Xwrapper.config'",
    
    # Restart the kiosk
    "echo '12345' | sudo -S systemctl restart kiosk.service",
    
    # Check the log
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
