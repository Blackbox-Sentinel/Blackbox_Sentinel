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

# Install openbox and python3-tk and x11-xserver-utils
print("[*] Installing openbox...")
stdin, stdout, stderr = client.exec_command("echo '12345' | sudo -S apt-get install -y openbox python3-tk x11-xserver-utils")
stdout.channel.recv_exit_status()

xinitrc_content = """#!/bin/bash
xset s off
xset -dpms
xset s noblank

openbox-session &

cat << 'EOF' > /home/admin/kiosk_ui.py
import tkinter as tk

root = tk.Tk()
root.attributes('-fullscreen', True)
root.configure(bg='black')

label = tk.Label(root, text="TOUCH SCREEN OPERATIONAL", fg="#00FF00", bg="black", font=("Courier", 24, "bold"))
label.pack(expand=True)

def exit_app(event):
    root.destroy()
root.bind('<Button-1>', exit_app)

root.mainloop()
EOF

python3 /home/admin/kiosk_ui.py
"""

sftp = client.open_sftp()
with sftp.file('/home/admin/.xinitrc', 'w') as f:
    f.write(xinitrc_content)
sftp.chmod('/home/admin/.xinitrc', 0o755)
sftp.close()

# Start X!
print("[*] Launching X...")
client.exec_command("echo '12345' | sudo -S sh -c 'nohup startx /home/admin/.xinitrc -- /usr/bin/X :0 vt1 -nocursor >/tmp/startx.log 2>&1 &'")

import time
time.sleep(3)

print("[*] startx.log output:")
stdin, stdout, stderr = client.exec_command("cat /tmp/startx.log")
for line in iter(stdout.readline, ""):
    print("   " + line.strip('\n'))

client.close()
