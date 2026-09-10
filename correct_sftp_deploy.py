import paramiko
import sys
import io
import time

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

kiosk_code = """import tkinter as tk

root = tk.Tk()
root.attributes('-fullscreen', True)
root.configure(bg='black')

boxes = []

def box_clicked(event, widget):
    widget.destroy()
    boxes.remove(widget)
    if not boxes:
        lbl = tk.Label(root, text="TOUCH VERIFIED\\nALL BOXES CLEARED!", fg="#00FF00", bg="black", font=("Helvetica", 16, "bold"))
        lbl.place(relx=0.5, rely=0.5, anchor='center')

positions = [
    (0.1, 0.1, "Top-Left"),
    (0.9, 0.1, "Top-Right"),
    (0.1, 0.9, "Bottom-Left"),
    (0.9, 0.9, "Bottom-Right"),
    (0.5, 0.5, "Center")
]

for rx, ry, text in positions:
    btn = tk.Label(root, text=text, bg="red", fg="white", font=("Helvetica", 12, "bold"), width=12, height=4, relief="raised")
    btn.place(relx=rx, rely=ry, anchor='center')
    btn.bind('<Button-1>', lambda e, b=btn: box_clicked(e, b))
    boxes.append(btn)

root.mainloop()
"""

xinitrc_code = """#!/bin/bash
xset s off
xset -dpms
xset s noblank

openbox-session &
python3 /home/admin/kiosk_ui.py
"""

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=5)
    
    sftp = client.open_sftp()
    
    print("[*] Uploading via SFTP to /tmp...")
    sftp.putfo(io.BytesIO(kiosk_code.encode('utf-8')), '/tmp/kiosk_ui.py')
    sftp.putfo(io.BytesIO(xinitrc_code.encode('utf-8')), '/tmp/.xinitrc')
    sftp.close()
    
    print("[*] Moving files to correct location and fixing ownership...")
    client.exec_command("echo '12345' | sudo -S mv /tmp/kiosk_ui.py /home/admin/kiosk_ui.py")
    client.exec_command("echo '12345' | sudo -S mv /tmp/.xinitrc /home/admin/.xinitrc")
    client.exec_command("echo '12345' | sudo -S chown admin:admin /home/admin/kiosk_ui.py /home/admin/.xinitrc")
    client.exec_command("echo '12345' | sudo -S chmod +x /home/admin/.xinitrc")
    
    print("[*] Restarting Sentinel Kiosk Service...")
    client.exec_command("echo '12345' | sudo -S killall -9 Xorg xinit startx python3 openbox sleep")
    time.sleep(2)
    client.exec_command("echo '12345' | sudo -S systemctl restart sentinel-kiosk.service")
    
    client.close()
    print("[*] Done!")
except Exception as e:
    print(f"Error: {e}")
