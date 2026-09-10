import paramiko
import socket
import sys
import base64

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

b64 = base64.b64encode(kiosk_code.encode('utf-8')).decode('utf-8')

print("[*] Deploying proper touch calibration UI via base64...")
client.exec_command(f"echo '{b64}' | base64 -d > /home/admin/kiosk_ui.py")

print("[*] Killing old X processes...")
client.exec_command("echo '12345' | sudo -S killall -9 Xorg xinit startx python3 openbox")
import time
time.sleep(2)

print("[*] Restarting Sentinel Kiosk Service...")
client.exec_command("echo '12345' | sudo -S systemctl restart sentinel-kiosk.service")

client.close()
