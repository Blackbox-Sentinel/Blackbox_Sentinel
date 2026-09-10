import paramiko
import sys

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
    print("[+] SSH Connected!")
except Exception as e:
    print(f"[-] SSH failed: {e}")
    sys.exit(1)

commands = [
    "rm -rf LCD-show",
    "git clone https://github.com/goodtft/LCD-show.git",
    "chmod -R 755 LCD-show",
    "cd LCD-show/ && ls -l",
    "cd LCD-show/ && echo '12345' | sudo -S ./LCD35-show"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    for line in iter(stdout.readline, ""):
        print("   " + line.strip())
    for line in iter(stderr.readline, ""):
        print("   [STDERR] " + line.strip())

client.close()
