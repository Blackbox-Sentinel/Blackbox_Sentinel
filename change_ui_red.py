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

kiosk_ui_red = """import tkinter as tk

root = tk.Tk()
# Try explicit geometry instead of fullscreen to be safe, e.g. 480x320 or 320x480
root.geometry("320x480+0+0")
root.configure(bg='red')

label = tk.Label(root, text="TOUCH SCREEN\\nOPERATIONAL", fg="white", bg="red", font=("Helvetica", 16, "bold"))
label.pack(expand=True)

def exit_app(event):
    root.destroy()
root.bind('<Button-1>', exit_app)

root.mainloop()
"""

xinitrc_content = """#!/bin/bash
xset s off
xset -dpms
xset s noblank

openbox-session &
python3 /home/admin/kiosk_ui.py
"""

print("[*] Changing UI to RED to debug...")
client.exec_command(f"echo \"{kiosk_ui_red}\" > /home/admin/kiosk_ui.py")
client.exec_command(f"echo \"{xinitrc_content}\" > /home/admin/.xinitrc")

print("[*] Restarting Sentinel Kiosk...")
client.exec_command("echo '12345' | sudo -S systemctl restart sentinel-kiosk.service")

client.close()
