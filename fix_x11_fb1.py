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
    # Tell X11 explicitly to use the SPI framebuffer (fb1) natively!
    """echo '12345' | sudo -S sh -c "cat << 'EOF' > /usr/share/X11/xorg.conf.d/99-fbdev.conf
Section \\"Device\\"
    Identifier \\"myfb\\"
    Driver \\"fbdev\\"
    Option \\"fbdev\\" \\"/dev/fb1\\"
EndSection
EOF" """,
    
    # We need to kill fbcp if X11 runs natively on fb1, otherwise they conflict!
    "echo '12345' | sudo -S killall fbcp 2>/dev/null",
    "echo '12345' | sudo -S sed -i 's/fbcp/\\#fbcp/' /etc/rc.local",
    
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
