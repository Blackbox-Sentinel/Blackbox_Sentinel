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
except Exception as e:
    print(f"Failed to connect: {e}")
    sys.exit(1)

commands = [
    "echo '12345' | sudo -S curl -L https://github.com/goodtft/LCD-show/raw/master/usr/tft35a-overlay.dtb -o /tmp/tft35a.dtbo",
    "ls -l /tmp/tft35a.dtbo",
    "echo '12345' | sudo -S mv /tmp/tft35a.dtbo /boot/firmware/overlays/tft35a.dtbo",
    "ls -l /boot/firmware/overlays/tft35a.dtbo",
    "echo '12345' | sudo -S sh -c 'echo \"hdmi_force_hotplug=1\" >> /boot/firmware/config.txt'",
    "echo '12345' | sudo -S sh -c 'echo \"dtparam=spi=on\" >> /boot/firmware/config.txt'",
    "echo '12345' | sudo -S sh -c 'echo \"dtoverlay=tft35a:rotate=90\" >> /boot/firmware/config.txt'",
    "cat /boot/firmware/config.txt | tail -n 5"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    
    # Block until finished
    out = stdout.read().decode('ascii', 'ignore')
    err = stderr.read().decode('ascii', 'ignore')
    if out: print("   OUT: " + out.strip().replace('\n', '\n   OUT: '))
    if err: print("   ERR: " + err.strip().replace('\n', '\n   ERR: '))

print("\n[*] Issuing reboot...")
try:
    client.exec_command("echo '12345' | sudo -S reboot -f")
    time.sleep(2)
except:
    pass

client.close()
print("[*] Script finished!")
