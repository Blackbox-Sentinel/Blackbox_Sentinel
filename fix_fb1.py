import paramiko
import time

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "1234"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

x11_conf = """Section "Device"
    Identifier "Displays"
    Driver "fbdev"
    Option "fbdev" "/dev/fb1"
EndSection
"""

try:
    print("[*] Fixing X11 frame buffer routing...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    # Write the correct config that routes the desktop to the SPI screen (/dev/fb1)
    # using the stable 'fbdev' driver instead of the broken 'fbturbo'
    cmd = f"""echo '{x11_conf}' > /tmp/99-fbdev.conf && \
             echo '1234' | sudo -S mv /tmp/99-fbdev.conf /usr/share/X11/xorg.conf.d/99-fbdev.conf && \
             echo '1234' | sudo -S systemctl restart lightdm"""
    
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    print("[+] Fixed frame buffer routing. Desktop should appear on the 3.5 screen now.")
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
