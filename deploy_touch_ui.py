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

kiosk_code = """import tkinter as tk

root = tk.Tk()
root.attributes('-fullscreen', True)
root.configure(bg='black')

boxes = []

def box_clicked(event, widget):
    widget.destroy()
    boxes.remove(widget)
    if not boxes:
        # All boxes clicked
        lbl = tk.Label(root, text="TOUCH VERIFIED\\nALL BOXES CLEARED!", fg="#00FF00", bg="black", font=("Helvetica", 16, "bold"))
        lbl.place(relx=0.5, rely=0.5, anchor='center')

# Create 4 boxes in corners and 1 in center
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

print("[*] Replacing kiosk_ui.py with touch verification boxes...")
client.exec_command(f"echo \"{kiosk_code}\" > /home/admin/kiosk_ui.py")

print("[*] Restarting Sentinel Kiosk Service...")
client.exec_command("echo '12345' | sudo -S systemctl restart sentinel-kiosk.service")

client.close()
