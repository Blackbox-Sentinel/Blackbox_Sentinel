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
    # Tell X11 explicitly to use the framebuffer device that the terminal is using
    """echo '12345' | sudo -S sh -c "cat << 'EOF' > /usr/share/X11/xorg.conf.d/99-fbdev.conf
Section \\"Device\\"
    Identifier \\"myfb\\"
    Driver \\"fbdev\\"
    Option \\"fbdev\\" \\"/dev/fb0\\"
EndSection
EOF" """,
    
    # Restart the kiosk service
    "echo '12345' | sudo -S systemctl restart kiosk.service",
    "sleep 3",
    "systemctl status kiosk.service -l --no-pager"
]

for cmd in commands:
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        for line in iter(stdout.readline, ""):
            pass
    except Exception:
        pass

client.close()
