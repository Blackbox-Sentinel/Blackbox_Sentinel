import paramiko
import time
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
    print("[+] SSH Connected!")
except Exception as e:
    print("[-] SSH Failed:", e)
    sys.exit(1)

commands = [
    # Install the browser, lightweight window manager, and unclutter (to hide the mouse pointer)
    "echo '12345' | sudo -S apt-get update",
    "echo '12345' | sudo -S apt-get install -y --no-install-recommends chromium-browser openbox unclutter x11-xserver-utils",
    
    # Create the X11 launch script
    """cat << 'EOF' > /home/admin/.xinitrc
#!/bin/bash
# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Hide mouse cursor
unclutter -idle 0.1 -root &

# Start window manager
openbox-session &

# Start Chromium in Kiosk mode
chromium-browser --noerrdialogs --disable-infobars --kiosk https://duckduckgo.com
EOF""",
    "chmod +x /home/admin/.xinitrc",
    
    # Create a systemd service to run startx automatically on boot
    """echo '12345' | sudo -S sh -c "cat << 'EOF' > /etc/systemd/system/kiosk.service
[Unit]
Description=Sentinel Kiosk UI
After=systemd-user-sessions.service

[Service]
User=admin
ExecStart=/usr/bin/startx /home/admin/.xinitrc -- -nocursor
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF" """,
    
    # Enable and start the service
    "echo '12345' | sudo -S systemctl daemon-reload",
    "echo '12345' | sudo -S systemctl enable kiosk.service",
    "echo '12345' | sudo -S systemctl start kiosk.service"
]

for cmd in commands:
    print(f"[*] Executing: {cmd[:50]}...")
    stdin, stdout, stderr = client.exec_command(cmd)
    for line in iter(stdout.readline, ""):
        print("   " + line.strip())

print("[+] Kiosk Mode Launched! Look at the screen!")
client.close()
