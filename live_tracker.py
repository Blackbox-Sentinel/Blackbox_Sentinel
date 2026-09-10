import tkinter as tk
from tkinter import ttk
import paramiko
import threading
import time
import socket

HOSTNAME = "sentinel.local"
USERNAME = "admin"
PASSWORD = "12345"
TOTAL_PACKAGES = 105

class InstallerTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("BlackBox Sentinel - Live Intel")
        self.root.geometry("550x220")
        self.root.configure(bg="#0d1117")
        self.root.attributes('-topmost', True)
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("green.Horizontal.TProgressbar", foreground='#00ff00', background='#00ff00', troughcolor='#161b22')

        self.title_label = tk.Label(root, text="SENTINEL LIVE TELEMETRY", fg="#00ff00", bg="#0d1117", font=("Courier", 16, "bold"))
        self.title_label.pack(pady=15)

        self.status_label = tk.Label(root, text="Establishing secure SSH link to Pi...", fg="#58a6ff", bg="#0d1117", font=("Courier", 10))
        self.status_label.pack(pady=5)

        self.progress = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=450, mode='determinate', style="green.Horizontal.TProgressbar")
        self.progress.pack(pady=15)
        self.progress['maximum'] = TOTAL_PACKAGES

        self.percent_label = tk.Label(root, text="0%", fg="#8b949e", bg="#0d1117", font=("Courier", 10))
        self.percent_label.pack()

        self.running = True
        self.thread = threading.Thread(target=self.poll_logs, daemon=True)
        self.thread.start()

    def poll_logs(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ip = socket.gethostbyname(HOSTNAME)
            client.connect(ip, username=USERNAME, password=PASSWORD, timeout=5)
            self.update_ui("Link Established! Scanning recovery progress...", 0)
        except Exception as e:
            self.update_ui(f"Connection Error: {e}", 0)
            return

        installed_pkgs = set()
        
        while self.running:
            try:
                stdin, stdout, stderr = client.exec_command("tail -n 300 /var/log/dpkg.log")
                lines = stdout.read().decode('ascii', 'ignore').splitlines()
                
                latest_action = "Analyzing dependencies..."
                for line in lines:
                    if "status unpacked" in line or "status installed" in line or "status half-configured" in line or "status half-installed" in line:
                        parts = line.split()
                        if len(parts) > 4:
                            pkg = parts[4]
                            installed_pkgs.add(pkg)
                            latest_action = f"Rebuilding: {pkg}"
                
                count = len(installed_pkgs)
                display_count = min(count, TOTAL_PACKAGES)
                
                if count >= TOTAL_PACKAGES:
                    latest_action = "Finalizing configuration and restarting graphics engine..."
                    display_count = TOTAL_PACKAGES
                
                self.update_ui(latest_action, display_count)
                
            except Exception:
                pass
            
            time.sleep(2)
            
        client.close()

    def update_ui(self, text, count):
        pct = min(100, int((count / TOTAL_PACKAGES) * 100))
        try:
            self.root.after(0, self.status_label.config, {'text': text})
            self.root.after(0, self.progress.config, {'value': count})
            self.root.after(0, self.percent_label.config, {'text': f"{count} / ~{TOTAL_PACKAGES} Packages Rebuilt ({pct}%)"})
        except tk.TclError:
            pass

    def on_closing(self):
        self.running = False
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = InstallerTracker(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
