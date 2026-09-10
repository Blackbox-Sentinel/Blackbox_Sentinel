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
    "cat /home/admin/.xsession-errors",
    "sudo journalctl -u sentinel-kiosk.service -n 20 --no-pager",
    "DISPLAY=:0 xrandr"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        output = stdout.read().decode('utf-8', errors='replace')
        print(output)
        err = stderr.read().decode('utf-8', errors='replace')
        if err:
            print("STDERR: " + err)
    except Exception as e:
        pass

client.close()
