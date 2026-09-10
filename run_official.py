import paramiko
import time
import sys
import socket

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

print("[*] Reconnecting to run the full official driver compiler...")

while True:
    try:
        ip = socket.gethostbyname(HOSTNAME)
        break
    except socket.gaierror:
        time.sleep(2)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(ip, username=USERNAME, password=PASSWORD, timeout=10)
    print("[+] SSH Connected!")
except Exception as e:
    print(f"[-] SSH failed: {e}")
    sys.exit(1)

commands = [
    # Remove any old clones
    "rm -rf LCD-show",
    
    # Clone the official repo
    "git clone https://github.com/goodtft/LCD-show.git",
    
    # Fix permissions
    "chmod -R 755 LCD-show",
    
    # Run the official installer which compiles fbcp and patches everything
    "cd LCD-show/ && echo '12345' | sudo -S ./LCD35-show"
]

full_cmd = " && ".join(commands)
print("[*] Executing official manufacturer script (this will take 2-3 minutes)...")

stdin, stdout, stderr = client.exec_command(full_cmd)

for line in iter(stdout.readline, ""):
    print(line, end="")

print("[+] Script complete! Pi is rebooting.")
client.close()
