import paramiko
import socket
import sys

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ip = socket.gethostbyname(HOSTNAME)
    client.connect(ip, username=USERNAME, password=PASSWORD, timeout=5)
except Exception as e:
    sys.exit(1)

commands = [
    # Try installing fbturbo
    "echo '12345' | sudo -S apt-get install -y xserver-xorg-video-fbturbo",
    
    # Force X11 to use the SPI framebuffer directly with ShadowFB disabled
    """echo '12345' | sudo -S sh -c "cat << 'EOF' > /usr/share/X11/xorg.conf.d/99-fbdev.conf
Section \\"Device\\"
    Identifier \\"myfb\\"
    Driver \\"fbdev\\"
    Option \\"fbdev\\" \\"/dev/fb1\\"
EndSection
EOF" """,
    
    # Kill fbcp again to avoid conflicts
    "echo '12345' | sudo -S killall fbcp 2>/dev/null",

    "echo '12345' | sudo -S systemctl restart kiosk.service",
    "sleep 3",
    "systemctl status kiosk.service -l --no-pager",
    "cat /var/log/Xorg.0.log | grep -E '(EE|WW|fb1)'"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        for line in iter(stdout.readline, ""):
            print("   " + line.strip('\n').encode('ascii', 'ignore').decode('ascii'))
    except Exception:
        pass

client.close()
