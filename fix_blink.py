import paramiko
import time

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

try:
    print("[*] Connecting to fix blinking screen...")
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=15)
    
    cmd = f"""echo '1234' | sudo -S systemctl stop lightdm && \
             echo '1234' | sudo -S rm -f /usr/share/X11/xorg.conf.d/99-fbdev.conf && \
             echo '{x11_conf}' > /tmp/99-fbturbo.conf && \
             echo '1234' | sudo -S mv /tmp/99-fbturbo.conf /usr/share/X11/xorg.conf.d/99-fbturbo.conf && \
             echo '1234' | sudo -S systemctl start lightdm"""
             
    stdin, stdout, stderr = client.exec_command(cmd)
    
    # wait for completion
    stdout.channel.recv_exit_status()
    print("[+] Restored fbturbo driver. Blinking should stop and desktop should load.")
    
except Exception as e:
    print(f"[-] Error: {e}")
finally:
    client.close()
