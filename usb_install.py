import paramiko
import time
import socket
import sys

USERNAMES = ["admin", "pi"]
PASSWORDS = ["12345", "raspberry"]
HOSTNAMES = ["sentinel.local", "raspberrypi.local"]

print("[*] Scanning network for Raspberry Pi via USB tethering bridge...")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

connected = False
for i in range(15):
    for host in HOSTNAMES:
        try:
            ip = socket.gethostbyname(host)
            print(f"[*] Found {host} at {ip}! Attempting SSH...")
            
            for user in USERNAMES:
                for pwd in PASSWORDS:
                    try:
                        client.connect(ip, username=user, password=pwd, timeout=5)
                        print(f"[+] Successfully connected as {user}:{pwd}")
                        connected = True
                        break
                    except paramiko.AuthenticationException:
                        pass
                    except Exception as e:
                        print(f"[-] SSH Error on {user}: {e}")
            
            if connected:
                break
        except socket.gaierror:
            print(f"[-] {host} not found yet...")
    
    if connected:
        break
    time.sleep(5)

if not connected:
    print("[-] Could not find Pi on the network bridge.")
    sys.exit(1)

# Now compile the driver
commands = [
    "sudo rm -rf LCD-show",
    "git clone https://github.com/goodtft/LCD-show.git",
    "chmod -R 755 LCD-show",
    f"cd LCD-show/ && echo '{pwd}' | sudo -S ./LCD35-show"
]

full_cmd = " && ".join(commands)

print("[*] Downloading and compiling GoodTFT LCD-show drivers... (This takes about 2-3 minutes)")
stdin, stdout, stderr = client.exec_command(full_cmd)

for line in iter(stdout.readline, ""):
    print(line, end="")

print("[+] Driver installed! Pi is rebooting...")
client.close()
