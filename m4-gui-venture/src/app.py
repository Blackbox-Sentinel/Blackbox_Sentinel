"""
BlackBox Sentinel — M4 GUI: Dashboard Application
800x480 Tkinter interface for real-time anomaly monitoring.

Author: M4 GUI/Venture Lead
Branch: m4-dev
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 480
BG_COLOR = "#0d1117"
ACCENT_COLOR = "#58a6ff"
ALERT_COLOR = "#f85149"
SUCCESS_COLOR = "#3fb950"
TEXT_COLOR = "#c9d1d9"


class SentinelDashboard:
    """Main dashboard window for BlackBox Sentinel."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BlackBox Sentinel — Network Monitor")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)
        
        self._build_header()
        self._build_status_panel()
        self._build_log_panel()
        self._build_footer()
    
    def _build_header(self):
        """Top header with title and status indicator."""
        header = tk.Frame(self.root, bg="#161b22", height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        title = tk.Label(
            header,
            text="🛡️ BlackBox Sentinel",
            font=("Consolas", 18, "bold"),
            fg=ACCENT_COLOR,
            bg="#161b22"
        )
        title.pack(side=tk.LEFT, padx=20, pady=10)
        
        status = tk.Label(
            header,
            text="● MONITORING",
            font=("Consolas", 12),
            fg=SUCCESS_COLOR,
            bg="#161b22"
        )
        status.pack(side=tk.RIGHT, padx=20, pady=10)
    
    def _build_status_panel(self):
        """Middle panel with system status cards."""
        panel = tk.Frame(self.root, bg=BG_COLOR)
        panel.pack(fill=tk.X, padx=20, pady=10)
        
        cards = [
            ("Packets Captured", "0", ACCENT_COLOR),
            ("Anomalies Detected", "0", ALERT_COLOR),
            ("Chain Length", "0", SUCCESS_COLOR),
            ("Uptime", "00:00:00", TEXT_COLOR),
        ]
        
        for label, value, color in cards:
            card = tk.Frame(panel, bg="#21262d", padx=15, pady=10)
            card.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5)
            
            tk.Label(card, text=label, font=("Consolas", 9), fg="#8b949e", bg="#21262d").pack()
            tk.Label(card, text=value, font=("Consolas", 20, "bold"), fg=color, bg="#21262d").pack()
    
    def _build_log_panel(self):
        """Scrollable log viewer for hash-chained entries."""
        log_frame = tk.Frame(self.root, bg=BG_COLOR)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        tk.Label(
            log_frame,
            text="📋 Hash-Chained Log",
            font=("Consolas", 12, "bold"),
            fg=TEXT_COLOR,
            bg=BG_COLOR,
            anchor="w"
        ).pack(fill=tk.X)
        
        self.log_text = tk.Text(
            log_frame,
            bg="#161b22",
            fg=TEXT_COLOR,
            font=("Consolas", 10),
            relief=tk.FLAT,
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Add sample log entry
        self._add_log("System initialized. Waiting for data from M2/M3...")
    
    def _build_footer(self):
        """Bottom status bar."""
        footer = tk.Frame(self.root, bg="#161b22", height=30)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        
        tk.Label(
            footer,
            text=f"BlackBox Sentinel v0.1 | {datetime.now().strftime('%Y-%m-%d')}",
            font=("Consolas", 9),
            fg="#8b949e",
            bg="#161b22"
        ).pack(side=tk.LEFT, padx=10, pady=5)
    
    def _add_log(self, message: str):
        """Append a message to the log panel."""
        self.log_text.configure(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
    
    def run(self):
        """Start the dashboard event loop."""
        self.root.mainloop()


if __name__ == "__main__":
    app = SentinelDashboard()
    app.run()
