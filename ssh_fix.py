import paramiko
import sys

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

print("[*] Reconnecting to fix driver URL...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=10)
    print("[+] SSH Connected!")
except Exception as e:
    print(f"[-] SSH connection failed: {e}")
    sys.exit(1)

commands = [
    # Download the CORRECT file (tft35a-overlay.dtb -> tft35a.dtbo)
    "echo '12345' | sudo -S wget -qO /boot/firmware/overlays/tft35a.dtbo https://raw.githubusercontent.com/goodtft/LCD-show/master/usr/tft35a-overlay.dtb",
    
    # Check if the file is there and valid
    "ls -l /boot/firmware/overlays/tft35a.dtbo",
    
    # Force reboot aggressively
    "echo '12345' | sudo -S reboot -f"
]

for cmd in commands:
    print(f"[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    
    if "reboot" not in cmd:
        for line in iter(stdout.readline, ""):
            print("   " + line.strip())

print("[+] Done. Sending forced reboot command.")
client.close()
