import paramiko

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"

code = """
import tkinter as tk
root = tk.Tk()
root.attributes("-fullscreen", True)
root.configure(bg="black")

def on_click(event):
    for w in root.winfo_children():
        w.configure(bg="grey")
    event.widget.configure(bg="red")

for r in range(3):
    root.grid_rowconfigure(r, weight=1)
    for c in range(3):
        root.grid_columnconfigure(c, weight=1)
        lbl = tk.Label(root, text=f"{r},{c}", bg="grey", fg="white", font=("Arial", 24))
        lbl.grid(row=r, column=c, sticky="nsew", padx=5, pady=5)
        lbl.bind("<Button-1>", on_click)

root.bind("<Escape>", lambda e: root.destroy())
root.mainloop()
"""

def run():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOSTNAME, username=USERNAME, password=PASSWORD)
    
    # Save the python script to the Pi
    ssh.exec_command(f"echo '{code}' > /home/admin/touch_test.py")
    
    # Run the script on the main display
    ssh.exec_command("DISPLAY=:0 python3 /home/admin/touch_test.py &")
    
    ssh.close()

if __name__ == '__main__':
    run()
