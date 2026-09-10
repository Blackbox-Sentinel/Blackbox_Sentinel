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

print("[*] Waiting for apt to finish...")
while True:
    stdin, stdout, stderr = client.exec_command("ps aux | grep apt-get | grep -v grep")
    output = stdout.read().decode()
    if not output.strip():
        break
    time.sleep(5)

print("[*] Apt finished! Starting X...")
client.exec_command("echo '12345' | sudo -S sh -c 'nohup startx /home/admin/.xinitrc -- /usr/bin/X :0 vt1 -nocursor >/tmp/startx.log 2>&1 &'")

client.close()
