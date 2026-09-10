import paramiko
import socket
import sys
import time

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

print("\n[*] Waiting for fresh OS to connect to Wi-Fi (this usually takes 1-2 minutes)...")
while True:
    try:
        ip = socket.gethostbyname(HOSTNAME)
        client.connect(ip, username=USERNAME, password=PASSWORD, timeout=5)
        print("[*] Connected! Injecting ultra-lightweight display drivers...")
        break
    except Exception:
        time.sleep(3)
        sys.stdout.write('.')
        sys.stdout.flush()

commands = [
    # 1. Download the exact pre-compiled dtbo driver for the 3.5" screen
    "wget https://raw.githubusercontent.com/goodtft/LCD-show/master/usr/tft35a-overlay.dtb -O tft35a.dtbo",
    "echo '12345' | sudo -S mv tft35a.dtbo /boot/overlays/tft35a.dtbo",
    
    # 2. Modify config.txt to enable the SPI screen
    "echo '12345' | sudo -S sh -c 'echo \"hdmi_force_hotplug=1\" >> /boot/config.txt'",
    "echo '12345' | sudo -S sh -c 'echo \"dtparam=spi=on\" >> /boot/config.txt'",
    "echo '12345' | sudo -S sh -c 'echo \"dtoverlay=tft35a:rotate=90\" >> /boot/config.txt'",
    
    # 3. Update apt and install extremely lightweight GUI (only ~80MB!)
    "echo '12345' | sudo -S apt-get update",
    "echo '12345' | sudo -S apt-get install --no-install-recommends -y xserver-xorg xserver-xorg-video-fbdev xserver-xorg-input-evdev xinit openbox xterm",
    
    # 4. Bind X11 directly to the SPI display (fb1)
    """echo '12345' | sudo -S sh -c "cat << 'EOF' > /usr/share/X11/xorg.conf.d/99-fbdev.conf
Section \\"Device\\"
    Identifier \\"myfb\\"
    Driver \\"fbdev\\"
    Option \\"fbdev\\" \\"/dev/fb1\\"
EndSection

Section \\"Monitor\\"
    Identifier \\"Monitor0\\"
EndSection

Section \\"Screen\\"
    Identifier \\"Screen0\\"
    Device \\"myfb\\"
    Monitor \\"Monitor0\\"
    DefaultDepth 16
EndSection
EOF" """,
    
    # 5. Create an xinitrc to launch a hacker terminal you can touch
    """echo '12345' | sudo -S sh -c "cat << 'EOF' > /home/admin/.xinitrc
#!/bin/sh
openbox-session &
exec xterm -fullscreen -bg black -fg green -e 'echo \"\n\n   TOUCH SCREEN OPERATIONAL!\n   TAP ANYWHERE ON THE SCREEN!\n\n\"; bash'
EOF" """,
    "echo '12345' | sudo -S chown admin:admin /home/admin/.xinitrc",
    "echo '12345' | sudo -S chmod +x /home/admin/.xinitrc",
    
    # 6. Auto-start GUI on boot
    """echo '12345' | sudo -S sh -c "cat << 'EOF' > /etc/systemd/system/gui.service
[Unit]
Description=Lightweight GUI
After=systemd-user-sessions.service

[Service]
User=admin
ExecStart=/usr/bin/startx /home/admin/.xinitrc
Restart=always

[Install]
WantedBy=multi-user.target
EOF" """,
    "echo '12345' | sudo -S systemctl enable gui.service",
    
    # 7. Reboot to apply kernel drivers!
    "echo '12345' | sudo -S reboot -f"
]

for cmd in commands:
    print(f"\n[*] Executing: {cmd.split()[0] if 'wget' in cmd else 'Configuring system...'}")
    stdin, stdout, stderr = client.exec_command(cmd)
    # Read output for apt-get so we know it finished
    if "apt-get" in cmd:
        try:
            for line in iter(stdout.readline, ""):
                print("   " + line.strip('\n'))
        except Exception:
            pass

client.close()
print("\n[*] SETUP COMPLETE! The Pi is rebooting right now. When it turns back on, the screen will light up!")
