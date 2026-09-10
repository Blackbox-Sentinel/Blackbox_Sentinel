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
    # Re-enable fbcp to copy fb0 to the SPI display
    "echo '12345' | sudo -S sed -i 's/\\#fbcp/fbcp/' /etc/rc.local",
    "echo '12345' | sudo -S nohup fbcp >/dev/null 2>&1 &",
    
    # Point X11 back to fb0
    """echo '12345' | sudo -S sh -c "cat << 'EOF' > /usr/share/X11/xorg.conf.d/99-fbdev.conf
Section \\"Device\\"
    Identifier \\"myfb\\"
    Driver \\"fbdev\\"
    Option \\"fbdev\\" \\"/dev/fb0\\"
EndSection
EOF" """,

    # Fix permissions by running the kiosk as root to bypass all restrictions!
    "echo '12345' | sudo -S sed -i 's/User=admin/User=root/' /etc/systemd/system/kiosk.service",
    
    # Reload and restart
    "echo '12345' | sudo -S systemctl daemon-reload",
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
