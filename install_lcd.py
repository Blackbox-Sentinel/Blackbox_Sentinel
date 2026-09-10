import paramiko
import time

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

print(f"[*] Connecting to {USERNAME}@{HOSTNAME}...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    print("[+] Successfully authenticated via SSH.")
    
    # We will run a compound command to clone the repo and run the installer
    # Note: LCD35-show script typically reboots the Pi automatically.
    commands = [
        "sudo rm -rf LCD-show",
        "git clone https://github.com/goodtft/LCD-show.git",
        "chmod -R 755 LCD-show",
        f"cd LCD-show/ && echo '{PASSWORD}' | sudo -S ./LCD35-show"
    ]
    
    full_cmd = " && ".join(commands)
    
    print("[*] Executing LCD-show driver installation script...")
    stdin, stdout, stderr = client.exec_command(full_cmd)
    
    # Read output line by line
    for line in iter(stdout.readline, ""):
        print(line, end="")
        
    print("[+] Driver installation sent. The Raspberry Pi should be rebooting now.")

except Exception as e:
    print(f"[-] Error during SSH connection or execution: {e}")
finally:
    client.close()
