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
    "cat /var/log/Xorg.0.log | grep -E '(EE|WW)'"
]

for cmd in commands:
    print(f"\n[*] Output of {cmd}:")
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        for line in iter(stdout.readline, ""):
            print("   " + line.strip('\n').encode('ascii', 'ignore').decode('ascii'))
    except Exception:
        pass

client.close()
