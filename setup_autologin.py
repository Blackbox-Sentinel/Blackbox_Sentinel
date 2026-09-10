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
except Exception:
    sys.exit(1)

commands = [
    # Enable automatic login to tty1
    "echo '12345' | sudo -S mkdir -p /etc/systemd/system/getty@tty1.service.d",
    """echo '12345' | sudo -S sh -c "cat << 'EOF' > /etc/systemd/system/getty@tty1.service.d/autologin.conf
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin admin --noclear %I \\$TERM
EOF" """,
    
    # Auto-start X11 as soon as autologin completes
    """echo '12345' | sudo -S sh -c "cat << 'EOF' > /home/admin/.bash_profile
if [ -z \\"\\$DISPLAY\\" ] && [ \\"\\$(tty)\\" = \\"/dev/tty1\\" ]; then
    startx
fi
EOF" """,
    "echo '12345' | sudo -S chown admin:admin /home/admin/.bash_profile",
    
    # Check why X11 crashed earlier (if it did)
    "cat /home/admin/.local/share/xorg/Xorg.0.log | grep -E '(EE)'",
    
    # Reload and restart the terminal instantly on screen!
    "echo '12345' | sudo -S systemctl daemon-reload",
    "echo '12345' | sudo -S systemctl restart getty@tty1.service"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd.split()[0] if 'cat' not in cmd else cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    try:
        for line in iter(stdout.readline, ""):
            print("   " + line.strip('\n'))
    except Exception:
        pass

client.close()
