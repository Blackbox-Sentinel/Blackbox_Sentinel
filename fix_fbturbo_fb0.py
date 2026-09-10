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
    # Force fbturbo to use fb0 (the internal HDMI framebuffer)
    """echo '12345' | sudo -S sh -c "cat << 'EOF' > /usr/share/X11/xorg.conf.d/99-fbturbo.conf
Section \\"Device\\"
    Identifier \\"fbturbo\\"
    Driver \\"fbturbo\\"
    Option \\"fbdev\\" \\"/dev/fb0\\"
    Option \\"SwapbuffersWait\\" \\"true\\"
EndSection
EOF" """,
    
    # Ensure fbcp is running to continuously copy fb0 -> fb1
    "echo '12345' | sudo -S nohup fbcp >/dev/null 2>&1 &",
    
    # Restart the kiosk service
    "echo '12345' | sudo -S systemctl restart kiosk.service",
    "sleep 3",
    "systemctl status kiosk.service -l --no-pager"
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
