import paramiko
import time
import socket

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "1234"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

x11_conf = """Section "Device"
    Identifier "Allwinner A10/A13 FBDEV"
    Driver "fbturbo"
    Option "fbdev" "/dev/fb1"
    Option "SwapbuffersWait" "true"
EndSection
"""

print("[*] Waiting for Pi to come online to push fix...")
for i in range(20):
    try:
        # Try to resolve IP first
        ip = socket.gethostbyname(HOSTNAME)
        print(f"[*] Found Pi at {ip}, connecting...")
        
        client.connect(ip, username=USERNAME, password=PASSWORD, timeout=10)
        
        cmd = f"""echo '1234' | sudo -S systemctl stop lightdm && \
                 echo '1234' | sudo -S rm -f /usr/share/X11/xorg.conf.d/99-fbdev.conf && \
                 echo '{x11_conf}' > /tmp/99-fbturbo.conf && \
                 echo '1234' | sudo -S mv /tmp/99-fbturbo.conf /usr/share/X11/xorg.conf.d/99-fbturbo.conf && \
                 echo '1234' | sudo -S systemctl start lightdm"""
                 
        stdin, stdout, stderr = client.exec_command(cmd)
        stdout.channel.recv_exit_status()
        print("[+] SUCCESS! Restored driver. Blinking should stop!")
        client.close()
        break
    except socket.gaierror:
        print("[-] Not on network yet. Retrying in 5s...")
        time.sleep(5)
    except Exception as e:
        print(f"[-] SSH Error: {e}. Retrying in 5s...")
        time.sleep(5)
