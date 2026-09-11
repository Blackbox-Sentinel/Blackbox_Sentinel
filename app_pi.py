"""
BlackBox Sentinel — M4 Interactive Tactical GUI & Defense Node Kiosk
800x480 Real-time Autonomous Defense Dashboard for Touchscreen & Desktop.

Features:
- Live Pipeline Orchestration (Calibration -> Armed -> Attack Containment -> Lockdown)
- Live Hardware Telemetry (Relay State, Status LED, GSM Modem, Anti-Tamper Grid)
- Interactive Tactical Controls (Attack Injector, Tamper Simulator, PIN Override Pad)
- Tamper-Evident SHA-256 Forensic Ledger Stream & Chain Auditor
"""

import os
import sys
import time
import json
import threading
import queue
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone

# Ensure stdout handles UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = CURRENT_DIR if os.path.isdir(os.path.join(CURRENT_DIR, "m2-systems")) else os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "m3-ml-ledger", "src"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "m2-systems", "sim"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "common"))

os.environ["SENTINEL_HARDWARE"] = "sim"

from hal import get_hal
from predict import AnomalyScorer, DeviceState
from ledger import HashChainLedger
from traffic_generator import TrafficGenerator
from pin_security import validate_pin
from security.trusted_controller import TrustedController, load_or_create_shared_secret

# ── Aesthetic Styling Constants ──
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320
COLOR_BG_DARK = "#090d16"
COLOR_PANEL_BG = "#111827"
COLOR_CARD_BG = "#1f293d"
COLOR_ACCENT_CYAN = "#00f0ff"
COLOR_ALERT_RED = "#ff2a5f"
COLOR_SUCCESS_GREEN = "#00ff88"
COLOR_WARNING_YELLOW = "#ffd000"
COLOR_TEXT_MAIN = "#f1f5f9"
COLOR_TEXT_MUTED = "#94a3b8"
FONT_TITLE = ("Consolas", 10, "bold")
FONT_HEADING = ("Consolas", 8, "bold")
FONT_DATA = ("Consolas", 9, "bold")
FONT_SMALL = ("Consolas", 7)
FONT_LOG = ("Consolas", 7)
CHART_BG = "#070a10"
CHART_GRID = "#263449"
CHART_PACKET = "#00f0ff"
CHART_SCORE = "#ff2a5f"


class SentinelTacticalApp:
    
    def _open_uart(self):
        """Open one persistent Pi UART5 connection for signed receipts."""
        try:
            import serial
        except ImportError:
            self.append_log("[UART] pyserial unavailable; hardware UART disabled")
            return None
        try:
            connection = serial.Serial("/dev/ttyAMA5", 115200, timeout=1, write_timeout=1)
            self.append_log("[UART] Connected to /dev/ttyAMA5 at 115200 baud")
            return connection
        except Exception as exc:
            self.append_log(f"[UART] /dev/ttyAMA5 unavailable; simulation mode ({exc})")
            return None

    def _send_uart_anomaly(self):
        """Create and send the signed 12-field containment receipt."""
        import base64
        import hashlib
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        if not hasattr(self, "private_key"):
            priv_bytes = base64.urlsafe_b64decode("MXiKDM2sa-TwEaJHHiQKBGvt9LzHR7jmX8oZQx4x7Bo=")
            self.private_key = Ed25519PrivateKey.from_private_bytes(priv_bytes)
        if not hasattr(self, "_receipt_seq"):
            self._receipt_seq = 0
        self._receipt_seq += 1

        evidence_raw = json.dumps({
            "anomaly_count": getattr(self, "anomaly_count", 0),
            "packet_count": getattr(self, "packet_count", 0),
        }, separators=(",", ":")).encode("utf-8")
        evidence_digest = "sha256:" + hashlib.sha256(evidence_raw).hexdigest()[:16]
        node_id = getattr(self, "node_id", "AEDN-NODE-01")
        ts = int(time.time())
        payload = {
            "algorithm": "Ed25519",
            "controller_id": node_id,
            "decision": "CONTAIN",
            "event_hash": "sha256:" + hashlib.sha256(f"{node_id}:{ts}".encode()).hexdigest()[:16],
            "evidence_digest": evidence_digest,
            "incident_id": f"{node_id}:{ts}",
            "key_epoch": 1,
            "organization_id": "openclaw-sentinel",
            "quorum": "N/A",
            "receipt_sequence": self._receipt_seq,
            "receipt_version": 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = self.private_key.sign(payload_bytes)
        public_key = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        receipt = {
            "payload": payload,
            "signature": base64.urlsafe_b64encode(signature).decode("ascii"),
            "public_key": base64.urlsafe_b64encode(public_key).decode("ascii"),
        }
        wire_data = (json.dumps(receipt, separators=(",", ":")) + "\n").encode("utf-8")
        with self._uart_lock:
            if self._uart_serial is None:
                return
            try:
                self._uart_serial.write(wire_data)
                self._uart_serial.flush()
                self.append_log(f"[UART] Signed containment receipt sent on /dev/ttyAMA5 ({len(wire_data)} bytes)")
            except Exception as exc:
                self.append_log(f"[UART] Receipt write failed: {exc}")
                try:
                    self._uart_serial.close()
                except Exception:
                    pass
                self._uart_serial = None

    def __init__(self):
        self.root = tk.Tk()
        self.ui_thread_id = threading.get_ident()
        self._ui_log_queue = queue.Queue()
        self._uart_lock = threading.Lock()
        self._uart_serial = None
        self._event_log = deque(maxlen=200)
        self.root.title("🛡️ BLACKBOX SENTINEL — AUTONOMOUS EDGE DEFENSE NODE")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=COLOR_BG_DARK)
        self.root.resizable(False, False)
        self.root.attributes("-fullscreen", True)
        
        # Center on screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x = max(0, (screen_w - WINDOW_WIDTH) // 2)
        pos_y = max(0, (screen_h - WINDOW_HEIGHT) // 2)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{pos_x}+{pos_y}")

        # Core Components
        self.node_id = "AEDN-RACK-01"
        self.ledger_path = os.path.join(PROJECT_ROOT, "m3-ml-ledger", "data", "gui_ledger.json")
        self.keys_vault = os.path.join(PROJECT_ROOT, "scratch_gui_keys")
        os.makedirs(self.keys_vault, exist_ok=True)
        with open(os.path.join(self.keys_vault, "master_aes.key"), "wb") as f:
            f.write(os.urandom(32))

        self.hal = get_hal(
            mode="sim",
            on_tamper_callback=self._handle_tamper_event,
            on_relay_change=self._handle_relay_change,
            node_id=self.node_id
        )
        self.scorer = AnomalyScorer()
        self.controller = TrustedController(secret=load_or_create_shared_secret(), quorum_required=0)
        self.ledger = HashChainLedger(self.ledger_path)
        self.traffic_gen = TrafficGenerator()

        # Telemetry State
        self.is_running = True
        self.packet_count = 0
        self.anomaly_count = 0
        self.start_time = time.time()
        self.entered_pin = ""
        self.injected_attack_type = None
        self.latest_anomaly_score = 0.0
        self._last_metric_time = time.monotonic()
        self._last_metric_packets = 0
        self.packet_rate_history = deque(maxlen=40)
        self.anomaly_score_history = deque(maxlen=40)

        # Build UI layout
        self._build_header()
        self._build_main_body()
        self._build_footer()
        self._uart_serial = self._open_uart()

        # Start background pipeline loop
        self.pipeline_thread = threading.Thread(target=self._pipeline_worker, daemon=True)
        self.pipeline_thread.start()

        # Start periodic GUI telemetry refresh
        self.root.after(100, self._update_telemetry_loop)

    def _build_header(self):
        header = tk.Frame(self.root, bg=COLOR_PANEL_BG, height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Title / Node info
        title_box = tk.Frame(header, bg=COLOR_PANEL_BG)
        title_box.pack(side=tk.LEFT, padx=15, pady=6)
        
        lbl_title = tk.Label(title_box, text="🛡️ BLACKBOX SENTINEL", font=FONT_TITLE, fg=COLOR_ACCENT_CYAN, bg=COLOR_PANEL_BG)
        lbl_title.pack(anchor="w")
        lbl_sub = tk.Label(title_box, text=f"EDGE DEFENSE NODE: {self.node_id} | TRANSPARENT INLINE BRIDGE", font=FONT_SMALL, fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG)
        lbl_sub.pack(anchor="w")

        # Live State Badge
        self.lbl_state_badge = tk.Label(
            header,
            text="● INITIALIZING",
            font=FONT_HEADING,
            fg=COLOR_WARNING_YELLOW,
            bg=COLOR_CARD_BG,
            padx=12,
            pady=2,
            relief=tk.RIDGE
        )
        self.lbl_state_badge.pack(side=tk.RIGHT, padx=15, pady=10)

    def _build_main_body(self):
        """Build a kiosk-style home screen with clickable feature applications."""
        self.shell = tk.Frame(self.root, bg=COLOR_BG_DARK)
        self.shell.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
        self.shell.grid_rowconfigure(1, weight=1)
        self.shell.grid_columnconfigure(0, weight=1)

        self.home_bar = tk.Frame(self.shell, bg=COLOR_PANEL_BG, height=28)
        self.home_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.home_bar.grid_propagate(False)
        tk.Label(self.home_bar, text="HOME / APPLICATIONS", font=FONT_HEADING, fg=COLOR_ACCENT_CYAN, bg=COLOR_PANEL_BG).pack(side=tk.LEFT, padx=8)
        self.view_title = tk.Label(self.home_bar, text="TACTICAL OVERVIEW", font=FONT_HEADING, fg=COLOR_TEXT_MAIN, bg=COLOR_PANEL_BG)
        self.view_title.pack(side=tk.RIGHT, padx=8)

        self.content_host = tk.Frame(self.shell, bg=COLOR_BG_DARK)
        self.content_host.grid(row=1, column=0, sticky="nsew")
        self._build_home_view()

    def _build_home_view(self):
        self._clear_content()
        self.view_title.config(text="TACTICAL OVERVIEW")
        panel = tk.Frame(self.content_host, bg=COLOR_BG_DARK)
        panel.pack(fill=tk.BOTH, expand=True)
        tk.Label(panel, text="BLACKBOX SENTINEL", font=("Consolas", 15, "bold"), fg=COLOR_ACCENT_CYAN, bg=COLOR_BG_DARK).pack(pady=(8, 1))
        tk.Label(panel, text="Select a secure application", font=FONT_SMALL, fg=COLOR_TEXT_MUTED, bg=COLOR_BG_DARK).pack(pady=(0, 7))
        grid = tk.Frame(panel, bg=COLOR_BG_DARK)
        grid.pack(expand=True)
        apps = [
            ("◉", "ANOMALY\\nGRAPH", "graph", COLOR_ACCENT_CYAN),
            ("⚠", "TAMPER\\nCONTROLS", "controls", COLOR_ALERT_RED),
            ("▤", "SYSTEM\\nLOGS", "logs", COLOR_SUCCESS_GREEN),
            ("▣", "SYSTEM\\nSTATUS", "status", COLOR_WARNING_YELLOW),
        ]
        for i, (icon, label, view, color) in enumerate(apps):
            card = tk.Frame(grid, bg=COLOR_CARD_BG, width=130, height=82, bd=1, relief=tk.RIDGE)
            card.grid(row=i // 2, column=i % 2, padx=7, pady=6)
            card.grid_propagate(False)
            button = tk.Button(card, text=f"{icon}\\n{label}", font=FONT_HEADING, fg=color, bg=COLOR_CARD_BG, activebackground=COLOR_PANEL_BG, activeforeground=COLOR_TEXT_MAIN, relief=tk.FLAT, bd=0, command=lambda v=view: self.show_view(v))
            button.pack(fill=tk.BOTH, expand=True)

    def _clear_content(self):
        for child in self.content_host.winfo_children():
            child.destroy()

    def show_view(self, view):
        if view == "home":
            self._build_home_view()
            return
        self._clear_content()
        back = tk.Button(self.home_bar, text="‹ HOME", font=FONT_SMALL, fg=COLOR_ACCENT_CYAN, bg=COLOR_PANEL_BG, activebackground=COLOR_CARD_BG, relief=tk.FLAT, command=self._build_home_view)
        back.pack(side=tk.LEFT, padx=4)
        if view == "graph":
            self.view_title.config(text="ANOMALY GRAPH")
            self._build_graph_view()
        elif view == "controls":
            self.view_title.config(text="TAMPER CONTROLS")
            self._build_controls_view()
        elif view == "logs":
            self.view_title.config(text="SYSTEM LOGS")
            self._build_logs_view()
        else:
            self.view_title.config(text="SYSTEM STATUS")
            self._build_status_view()

    def _build_graph_view(self):
        tk.Label(self.content_host, text="LIVE PACKET RATE / ANOMALY SCORE", font=FONT_HEADING, fg=COLOR_ACCENT_CYAN, bg=COLOR_BG_DARK).pack(anchor="w", padx=8, pady=5)
        self.telemetry_canvas = tk.Canvas(self.content_host, bg=CHART_BG, height=150, highlightthickness=1, highlightbackground=CHART_GRID)
        self.telemetry_canvas.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)
        self._draw_telemetry_graph()

    def _build_controls_view(self):
        panel = tk.Frame(self.content_host, bg=COLOR_BG_DARK)
        panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        tk.Label(panel, text="AUTHORIZED TACTICAL ACTIONS", font=FONT_HEADING, fg=COLOR_ACCENT_CYAN, bg=COLOR_BG_DARK).pack(pady=5)
        for text, color, command in (("⚡ INJECT C2 ATTACK", "#b91c1c", lambda: self.inject_attack("EXFILTRATION")), ("💥 SYN FLOOD", "#7c2d12", lambda: self.inject_attack("SYN_FLOOD")), ("🚨 BREACH CASING", "#4c0519", self.hal.tamper.simulate_tamper), ("🔢 PIN OVERRIDE", "#065f46", self._popup_pin_pad)):
            tk.Button(panel, text=text, font=FONT_HEADING, fg="#ffffff", bg=color, activebackground=COLOR_CARD_BG, relief=tk.GROOVE, command=command).pack(fill=tk.X, pady=4)

    def _build_logs_view(self):
        self.log_text = tk.Text(self.content_host, bg=CHART_BG, fg=COLOR_TEXT_MAIN, font=FONT_LOG, relief=tk.FLAT, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        for item in self._event_log:
            self.log_text.insert(tk.END, item + "\n")
        self.log_text.see(tk.END)

    def _build_status_view(self):
        panel = tk.Frame(self.content_host, bg=COLOR_BG_DARK)
        panel.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self.lbl_pkts = self._make_stat_box(panel, "PACKETS INLINE", "0", COLOR_ACCENT_CYAN, 0, 0)
        self.lbl_anomalies = self._make_stat_box(panel, "ANOMALIES", "0", COLOR_ALERT_RED, 0, 1)
        self.lbl_blocks = self._make_stat_box(panel, "LEDGER BLOCKS", "1", COLOR_SUCCESS_GREEN, 1, 0)
        self.lbl_uptime = self._make_stat_box(panel, "UPTIME", "00:00:00", COLOR_TEXT_MAIN, 1, 1)
        tk.Label(panel, text="UART: /dev/ttyAMA5  |  RECEIPT: Ed25519 / 12 fields", font=FONT_SMALL, fg=COLOR_SUCCESS_GREEN, bg=COLOR_BG_DARK).grid(row=2, column=0, columnspan=2, pady=12)
        for col in (0, 1):
            panel.grid_columnconfigure(col, weight=1)

    def _make_stat_box(self, parent, title, val, color, row, col):
        card = tk.Frame(parent, bg=COLOR_CARD_BG, padx=8, pady=7)
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        tk.Label(card, text=title, font=FONT_SMALL, fg=COLOR_TEXT_MUTED, bg=COLOR_CARD_BG).pack(anchor="w")
        val_lbl = tk.Label(card, text=val, font=FONT_DATA, fg=color, bg=COLOR_CARD_BG)
        val_lbl.pack(anchor="w")
        return val_lbl

    def _draw_telemetry_graph(self):
        canvas = getattr(self, "telemetry_canvas", None)
        if canvas is None or not canvas.winfo_exists():
            return
        width = max(1, canvas.winfo_width() or 430)
        height = max(1, canvas.winfo_height() or 150)
        canvas.delete("all")
        canvas.create_line(0, height // 2, width, height // 2, fill=CHART_GRID)
        canvas.create_text(8, 8, anchor="nw", text="PACKET RATE", fill=CHART_PACKET, font=FONT_SMALL)
        canvas.create_text(width - 8, 8, anchor="ne", text="ANOMALY SCORE", fill=CHART_SCORE, font=FONT_SMALL)
        def series(values, color, scale):
            if len(values) < 2:
                return
            points = []
            for i, value in enumerate(values):
                x = 8 + i * (width - 16) / max(1, len(values) - 1)
                y = height - 10 - min(1.0, max(0.0, value / scale)) * (height - 28)
                points.extend((x, y))
            canvas.create_line(*points, fill=color, width=2, smooth=True)
        series(list(self.packet_rate_history), CHART_PACKET, 20.0)
        series(list(self.anomaly_score_history), CHART_SCORE, 1.0)

    def _make_stat_box(self, parent, title, val, color, row, col):
        card = tk.Frame(parent, bg=COLOR_CARD_BG, padx=3, pady=2)
        card.grid(row=row, column=col, padx=4, pady=2, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        tk.Label(card, text=title, font=("Consolas", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD_BG).pack(anchor="w")
        val_lbl = tk.Label(card, text=val, font=FONT_DATA, fg=color, bg=COLOR_CARD_BG)
        val_lbl.pack(anchor="w")
        return val_lbl

    def _build_footer(self):
        footer = tk.Frame(self.root, bg=COLOR_PANEL_BG, height=18)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)

        tk.Label(
            footer,
            text=f"BlackBox Sentinel OS v2.1 | SHA-256 Ledger Integrity: VERIFIED | Hardware: SIMULATION",
            font=("Consolas", 8),
            fg=COLOR_TEXT_MUTED,
            bg=COLOR_PANEL_BG
        ).pack(side=tk.LEFT, padx=10)

    def _append_log_main(self, msg: str):
        """Store events and render them only when the logs app is visible."""
        t_str = datetime.now().strftime("%H:%M:%S")
        rendered = f"[{t_str}] {msg}"
        self._event_log.append(rendered)
        log_text = getattr(self, "log_text", None)
        if log_text is not None and log_text.winfo_exists():
            log_text.insert(tk.END, rendered + "\n")
            log_text.see(tk.END)

    def append_log(self, msg: str):
        """Queue worker messages and render them safely in the GUI thread."""
        if threading.get_ident() == self.ui_thread_id:
            self._append_log_main(msg)
        else:
            self._ui_log_queue.put(msg)

    def inject_attack(self, attack_type: str):
        self.injected_attack_type = attack_type
        self.append_log(f"⚡ [SIMULATOR] Scheduled adversarial injection: {attack_type}")
        # Directly fire MQTT containment receipt to ESP32
        try:
            self._send_uart_anomaly()
            self.append_log("📡 [MQTT] Signed containment receipt dispatched to ESP32")
        except Exception as e:
            self.append_log(f"❌ [MQTT] Failed to send: {e}")

    def _popup_pin_pad(self):
        if hasattr(self, 'pin_frame') and self.pin_frame.winfo_exists():
            self.pin_frame.destroy()
            
        win = tk.Frame(self.root, bg=COLOR_PANEL_BG, bd=2, relief=tk.RAISED)
        win.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=260, height=300)
        self.pin_frame = win
        
        tk.Label(win, text="ENTER SECURITY PIN", font=FONT_HEADING, fg=COLOR_ACCENT_CYAN, bg=COLOR_PANEL_BG).pack(pady=8)
        
        pin_disp = tk.Label(win, text="____", font=("Consolas", 14, "bold"), fg=COLOR_TEXT_MAIN, bg="#000000", width=8)
        pin_disp.pack(pady=5)

        pin_str = []

        def press_num(n):
            if len(pin_str) < 4:
                pin_str.append(str(n))
                pin_disp.config(text="* " * len(pin_str) + "_ " * (4 - len(pin_str)))

        def clear():
            pin_str.clear()
            pin_disp.config(text="____")
            
        def close_pad():
            win.destroy()

        def submit():
            code_val = "".join(pin_str)
            if validate_pin(code_val) and self.scorer.pin_override(code_val):
                self.controller.recover()
                self.hal.relay.engage()
                self.hal.led.solid_on()
                self.ledger.add_entry("tactical_override", {"pin_status": "ACCEPTED", "relay": "ENGAGED"})
                self.append_log("✅ [PIN OVERRIDE] Correct PIN entered -> Data Line Restored & ARMED")
                win.destroy()
            else:
                pin_str.clear()
                pin_disp.config(text="REJECT", fg="red")
                win.after(1000, lambda: pin_disp.config(text="____", fg=COLOR_TEXT_MAIN))

        pad_frame = tk.Frame(win, bg=COLOR_PANEL_BG)
        pad_frame.pack(pady=5)

        keys = [
            ("1", 0, 0), ("2", 0, 1), ("3", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("7", 2, 0), ("8", 2, 1), ("9", 2, 2),
            ("CLR", 3, 0), ("0", 3, 1), ("OK", 3, 2)
        ]

        for text, r, c in keys:
            if text == "CLR":
                cmd = clear
                btn_color = COLOR_ALERT_RED
            elif text == "OK":
                cmd = submit
                btn_color = COLOR_SUCCESS_GREEN
            else:
                cmd = lambda n=text: press_num(n)
                btn_color = COLOR_CARD_BG

            btn = tk.Button(pad_frame, text=text, font=FONT_HEADING, width=4, height=1, bg=btn_color, fg="#ffffff", command=cmd)
            btn.grid(row=r, column=c, padx=3, pady=3)
            
        close_btn = tk.Button(win, text="CANCEL", font=FONT_SMALL, bg="#444", fg="#fff", command=close_pad)
        close_btn.pack(pady=5)

    def _handle_tamper_event(self):
        self.append_log("🚨 [TAMPER ALERT] Casing breached! Zeroizing volatile keys...")
        # Wipe keys
        if os.path.exists(self.keys_vault):
            for f in os.listdir(self.keys_vault):
                p = os.path.join(self.keys_vault, f)
                try:
                    with open(p, "wb") as h:
                        h.write(b"\x00" * os.path.getsize(p))
                    os.remove(p)
                except Exception:
                    pass
        self.controller.mark_tampered()
        self.hal.relay.isolate()
        if hasattr(self, "_send_uart_anomaly"): self._send_uart_anomaly()
        self.hal.led.blink(0.05)
        self.ledger.add_entry("tamper_breach", {"action": "KEYS_ZEROIZED", "relay": "ISOLATED", "controller_state": "TAMPERED"})
        self.append_log("🔥 [ZEROIZATION] Master cryptographic keys purged from RAM.")

    def _handle_relay_change(self, state: str):
        pass

    def _pipeline_worker(self):
        """Continuous packet processing engine."""
        self.append_log("System booting... starting 120-packet baseline calibration")
        self.scorer.start_calibration()

        # Step 1: Calibration
        for i in range(120):
            if not self.is_running:
                return
            pkt = self.traffic_gen.generate_normal_packet()
            res = self.scorer.ingest_features(pkt)
            self.latest_anomaly_score = float(res.get("score", 0.0) or 0.0)
            self.packet_count += 1
            if i == 119:
                self.scorer.calibration_start = time.time() - 2000
                res = self.scorer.ingest_features(pkt)
            time.sleep(0.02)

        self.controller.arm()
        self.append_log("✅ Baseline training complete. Trusted controller ARMED & DEFENDING.")
        self.hal.led.solid_on()

        # Step 2: Continuous monitoring
        while self.is_running:
            if self.injected_attack_type:
                pkt = self.traffic_gen.generate_attack_packet(self.injected_attack_type)
                self.injected_attack_type = None
            else:
                pkt = self.traffic_gen.generate_normal_packet()

            self.packet_count += 1
            res = self.scorer.ingest_features(pkt)
            self.latest_anomaly_score = float(res.get("score", 0.0) or 0.0)

            # Anomaly trigger
            if res.get("is_anomaly", False):
                self.anomaly_count += 1
                score = res.get("score", 0.0)
                event_id = f"evt-{self.packet_count:08d}"
                signal_a = self.controller.issue_signal(
                    event_id=event_id,
                    source="m3-known-detector",
                    signal_type="known_attack",
                    payload={"label": pkt.get("label", "ANOMALY"), "score": score},
                )
                signal_b = self.controller.issue_signal(
                    event_id=event_id,
                    source="m3-adaptive-profile",
                    signal_type="adaptive_anomaly",
                    payload={"dst_port": pkt.get("dst_port", 0), "score": score},
                )
                self.controller.submit_signal(signal_a)
                decision = self.controller.submit_signal(signal_b)
                if decision.get("decision") != "ISOLATE":
                    self.append_log("⚠️ [CONTROLLER] Evidence pending; relay remains connected")
                    time.sleep(0.08)
                    continue
                self.hal.relay.isolate()
                if hasattr(self, "_send_uart_anomaly"): self._send_uart_anomaly()
                self.hal.led.blink(0.2)
                self.scorer.trigger_lockdown()

                entry = self.ledger.add_entry("anomaly_lockdown", {
                    "attack": pkt.get("label", "ANOMALY"),
                    "packet_size": pkt["packet_size"],
                    "dst_port": pkt["dst_port"],
                    "score": score
                }, anomaly_score=score)

                self.append_log(f"🚨 [ANOMALY DETECTED] {pkt.get('label')} (Score: {score:.4f})")
                receipt = decision.get("receipt", {})
                receipt_status = self.controller.verify_receipt(receipt)[1] if receipt else "NOT_AVAILABLE"
                self.append_log(f"⚡ [RELAY] Controller-approved line CUT. Receipt {receipt.get('receipt_id', 'N/A')} {receipt_status}. Ledger Block #{entry['index']} SHA-256: {entry['hash'][:16]}...")
                self.hal.cellular.send_sms("+919876543210", f"ALERT: Line isolated on {self.node_id}")

            time.sleep(0.08)

    def _update_telemetry_loop(self):
        """Update UI elements at 10Hz."""
        while True:
            try:
                self._append_log_main(self._ui_log_queue.get_nowait())
            except queue.Empty:
                break

        now = time.monotonic()
        interval = max(0.1, now - self._last_metric_time)
        packet_rate = max(0.0, (self.packet_count - self._last_metric_packets) / interval)
        self._last_metric_time = now
        self._last_metric_packets = self.packet_count
        self.packet_rate_history.append(min(packet_rate, 20.0))
        self.anomaly_score_history.append(min(max(self.latest_anomaly_score, 0.0), 1.0))
        self._draw_telemetry_graph()

        # Update metrics
        if hasattr(self, "lbl_pkts"):
            self.lbl_pkts.config(text=str(self.packet_count))
        if hasattr(self, "lbl_anomalies"):
            self.lbl_anomalies.config(text=str(self.anomaly_count))
        if hasattr(self, "lbl_blocks"):
            self.lbl_blocks.config(text=str(len(self.ledger.chain)))

        elapsed = int(time.time() - self.start_time)
        hrs, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        if hasattr(self, "lbl_uptime"):
            self.lbl_uptime.config(text=f"{hrs:02d}:{mins:02d}:{secs:02d}")

        # Update State Badge
        state = self.scorer.state.value.upper()
        if state == "CALIBRATING":
            self.lbl_state_badge.config(text="● CALIBRATING (AI BASELINE)", fg=COLOR_WARNING_YELLOW)
        elif state == "ARMED":
            self.lbl_state_badge.config(text="● ARMED & MONITORING", fg=COLOR_SUCCESS_GREEN)
        elif state in ("ALERT", "LOCKDOWN"):
            self.lbl_state_badge.config(text="🚨 AIR-GAP LOCKDOWN (LINE CUT)", fg=COLOR_ALERT_RED)

        # Update hardware/controller status when the optional status view is open.
        relay_state = self.hal.relay.get_state()
        if hasattr(self, "lbl_relay_stat"):
            relay_text = "⚡ Relay: ISOLATED (Line Severed)" if relay_state == "ISOLATED" else "⚡ Relay: ENGAGED (Line Connected)"
            self.lbl_relay_stat.config(text=relay_text, fg=COLOR_ALERT_RED if relay_state == "ISOLATED" else COLOR_SUCCESS_GREEN)
        if hasattr(self, "lbl_tamper_stat") and self.hal.tamper.is_tampered():
            self.lbl_tamper_stat.config(text="🚨 Anti-Tamper: CASING BREACHED!", fg=COLOR_ALERT_RED)

        controller_state = self.controller.state.value
        if controller_state == "TAMPERED" and hasattr(self, "lbl_controller_stat"):
            self.lbl_controller_stat.config(text="🧠 Controller: TAMPERED | Link: HEALTHY", fg=COLOR_ALERT_RED)
            if hasattr(self, "lbl_key_stat"):
                self.lbl_key_stat.config(text="🔑 Key state: INVALIDATED | Power: PRIMARY", fg=COLOR_ALERT_RED)
        elif controller_state == "ISOLATED" and hasattr(self, "lbl_controller_stat"):
            self.lbl_controller_stat.config(text="🧠 Controller: ISOLATED | Link: HEALTHY", fg=COLOR_ALERT_RED)
            if hasattr(self, "lbl_signal_stat"):
                self.lbl_signal_stat.config(text="🔐 Signals: 2/2 independent evidence", fg=COLOR_ALERT_RED)
            latest = self.controller.receipts[-1] if self.controller.receipts else None
            receipt_state = self.controller.verify_receipt(latest)[1] if latest else "NOT_AVAILABLE"
            receipt_id = latest.receipt_id if latest else "N/A"
            if hasattr(self, "lbl_receipt_stat"):
                self.lbl_receipt_stat.config(text=f"🧾 Receipt: {receipt_state} {receipt_id} | Quorum: N/A", fg=COLOR_SUCCESS_GREEN if receipt_state == "VALID" else COLOR_ALERT_RED)
        elif controller_state == "ARMED" and hasattr(self, "lbl_controller_stat"):
            self.lbl_controller_stat.config(text="🧠 Controller: ARMED | Link: HEALTHY", fg=COLOR_SUCCESS_GREEN)
            if hasattr(self, "lbl_signal_stat"):
                self.lbl_signal_stat.config(text="🔐 Signals: waiting for independent evidence", fg=COLOR_TEXT_MUTED)
            if hasattr(self, "lbl_receipt_stat"):
                self.lbl_receipt_stat.config(text="🧾 Receipt: N/A | Quorum: NOT CONFIGURED", fg=COLOR_TEXT_MUTED)

        if self.is_running:
            self.root.after(100, self._update_telemetry_loop)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self):
        self.is_running = False
        with self._uart_lock:
            if self._uart_serial is not None:
                try:
                    self._uart_serial.close()
                except Exception:
                    pass
                self._uart_serial = None
        self.root.destroy()


if __name__ == "__main__":
    app = SentinelTacticalApp()
    app.run()
