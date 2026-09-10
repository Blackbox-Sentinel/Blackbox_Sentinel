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
root.config(cursor="none") # Hide mouse cursor for touch kiosk

# Main Container
frame = tk.Frame(root, bg='black')
frame.place(relx=0.5, rely=0.5, anchor='center')

# Title
lbl_title = tk.Label(frame, text="SENTINEL KIOSK", fg="#00FF00", bg="black", font=("Courier", 24, "bold"))
lbl_title.pack(pady=10)

# Status
lbl_status = tk.Label(frame, text="SYSTEM ONLINE\\nTOUCH SENSORS: OK", fg="white", bg="black", font=("Courier", 14))
lbl_status.pack(pady=10)

def pulse():
    current_color = lbl_title.cget("fg")
    next_color = "#005500" if current_color == "#00FF00" else "#00FF00"
    lbl_title.config(fg=next_color)
    root.after(1000, pulse)

pulse()
root.mainloop()
"""

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOSTNAME, username=USERNAME, password=PASSWORD, timeout=5)
    
    sftp = client.open_sftp()
    
    print("[*] Uploading final kiosk_ui.py via SFTP to /tmp...")
    sftp.putfo(io.BytesIO(kiosk_code.encode('utf-8')), '/tmp/kiosk_ui.py')
    sftp.close()
    
    print("[*] Moving file to correct location and fixing ownership...")
    client.exec_command("echo '12345' | sudo -S mv /tmp/kiosk_ui.py /home/admin/kiosk_ui.py")
    client.exec_command("echo '12345' | sudo -S chown admin:admin /home/admin/kiosk_ui.py")
    
    print("[*] Restarting Sentinel Kiosk Service...")
    client.exec_command("echo '12345' | sudo -S killall -9 Xorg xinit startx python3 openbox sleep")
    time.sleep(2)
    client.exec_command("echo '12345' | sudo -S systemctl restart sentinel-kiosk.service")
    
    client.close()
    print("[*] Final deployment complete!")
except Exception as e:
    print(f"Error: {e}")
