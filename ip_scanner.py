import paramiko
import socket
import concurrent.futures
import time
import sys

USERNAMES = ["admin", "pi"]
PASSWORDS = ["12345", "raspberry"]
SUBNETS = ["192.168.42", "192.168.43", "192.168.225"] # Common Android Tether Subnets

print("[*] Performing aggressive IP scan across Android Tether subnets...")

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

def try_ssh(ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    result = sock.connect_ex((ip, 22))
    sock.close()
    
    if result == 0:
        for u in USERNAMES:
            for p in PASSWORDS:
                try:
                    c = paramiko.SSHClient()
                    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    c.connect(ip, username=u, password=p, timeout=2)
                    return (True, ip, u, p)
                except:
                    pass
    return (False, None, None, None)

ips_to_scan = []
for sub in SUBNETS:
    for i in range(1, 255):
        ips_to_scan.append(f"{sub}.{i}")

with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    results = executor.map(try_ssh, ips_to_scan)
    
found_ip = None
for r in results:
    if r[0]:
        found_ip = r[1]
        found_user = r[2]
        found_pwd = r[3]
        break

if not found_ip:
    print("[-] Scan complete. Pi not found. USB connection might not be bridging.")
    sys.exit(1)

print(f"[+] SUCCESS! Found Pi at {found_ip} with {found_user}:{found_pwd}")

client.connect(found_ip, username=found_user, password=found_pwd, timeout=5)

commands = [
    "sudo rm -rf LCD-show",
    "git clone https://github.com/goodtft/LCD-show.git",
    "chmod -R 755 LCD-show",
    f"cd LCD-show/ && echo '{found_pwd}' | sudo -S ./LCD35-show"
]

full_cmd = " && ".join(commands)

print("[*] Downloading and compiling drivers... (2 minutes)")
stdin, stdout, stderr = client.exec_command(full_cmd)

for line in iter(stdout.readline, ""):
    print(line, end="")

print("[+] Done! Pi is rebooting...")
client.close()
