import paramiko
import time
import socket
import sys

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

print("[*] Waiting for Raspberry Pi to come online on Wi-Fi...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Loop until it is available
connected = False
for i in range(30):
    try:
        ip = socket.gethostbyname(HOSTNAME)
        print(f"[*] Found Pi at {ip}! Attempting SSH...")
        client.connect(ip, username=USERNAME, password=PASSWORD, timeout=10)
        connected = True
        break
    except socket.gaierror:
        print("[-] Still booting/connecting to Wi-Fi... waiting 5 seconds.")
        time.sleep(5)
    except Exception as e:
        print(f"[-] SSH not ready yet: {e}. Retrying...")
        time.sleep(5)

if not connected:
    print("[-] Could not connect after 2.5 minutes.")
    sys.exit(1)

print("[+] Successfully authenticated via SSH.")

commands = [
    "sudo rm -rf LCD-show",
    "git clone https://github.com/goodtft/LCD-show.git",
    "chmod -R 755 LCD-show",
    f"cd LCD-show/ && echo '{PASSWORD}' | sudo -S ./LCD35-show"
]

full_cmd = " && ".join(commands)

print("[*] Executing LCD-show driver installation script... (This takes about 2 minutes)")
stdin, stdout, stderr = client.exec_command(full_cmd)

# Read output
for line in iter(stdout.readline, ""):
    print(line, end="")

print("[+] Driver installation sent! The Pi is rebooting now.")
client.close()
