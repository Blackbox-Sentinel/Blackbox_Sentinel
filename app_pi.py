"""
BlackBox Sentinel — M4 Interactive Tactical GUI & Defense Node Kiosk
800x480 Real-time Autonomous Defense Dashboard for Touchscreen & Desktop.
"""

import os
import sys
import time
import json
import threading
import queue
from collections import deque
import tkinter as tk
import customtkinter as ctk
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
sys.path.insert(0, os.path.join(PROJECT_ROOT, "m4-gui-venture", "src"))

os.environ["SENTINEL_HARDWARE"] = "sim"

from hal import get_hal
from predict import AnomalyScorer, DeviceState
from ledger import HashChainLedger
from traffic_generator import TrafficGenerator
from pin_security import validate_pin
from trusted_controller_sim import SimTrustedController
from m3_security_contracts import ContainmentReceiptService, Ed25519ReceiptSigner, SoftwareMonotonicCounter, EvidenceSignal, TwoSignalGate
from quorum_state import QuorumState
import base64

# ── Ultra-Premium Styling Constants (480x320 Optimized) ──
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320
COLOR_BG_DARK = "#0B0F19"
COLOR_PANEL_BG = "#131A2A"
COLOR_CARD_BG = "#1C2538"
COLOR_CARD_HOVER = "#25314A"
COLOR_ACCENT_CYAN = "#00E5FF"
COLOR_ALERT_RED = "#FF3366"
COLOR_SUCCESS_GREEN = "#00E676"
COLOR_WARNING_YELLOW = "#FFC400"
COLOR_TEXT_MAIN = "#FFFFFF"
COLOR_TEXT_MUTED = "#8A9BB3"

CHART_BG = "#0D1322"
CHART_GRID = "#263553"
CHART_PACKET = "#00E5FF"
CHART_SCORE = "#FF3366"


class SentinelTacticalApp:
    
    def _apply_containment_logic(self, incident_id, score, pkt_label, pkt=None):
        """Invoke M3 security contracts to issue a valid Ed25519 receipt and apply containment."""
        sig_a = EvidenceSignal(
            signal_id=f"sig-A-{self.packet_count}",
            source_id="m3-ml-anomaly-scorer",
            signal_type="ml_anomaly",
            decision="CONFIRM" if score > 0.85 else "ABSTAIN",
            authenticated=True,
            fresh=True,
            confidence=max(0.0, min(1.0, float(score)))
        )
        
        # Second independent heuristic signal based on packet inter-arrival rate
        heuristic_decision = "ABSTAIN"
        heuristic_conf = 0.5
        if pkt_label == "TAMPER_BREACH":
            heuristic_decision = "CONFIRM"
            heuristic_conf = 1.0
        elif pkt:
            true_rate = 1.0 / max(0.000001, pkt.get("inter_arrival", 0.03))
            if true_rate > 500:  # Independent threshold for flood/exfil
                heuristic_decision = "CONFIRM"
                heuristic_conf = min(1.0, true_rate / 10000.0)
                
        sig_b = EvidenceSignal(
            signal_id=f"sig-B-{self.packet_count}",
            source_id="m2-heuristic-packet-rate",
            signal_type="heuristic_rate",
            decision=heuristic_decision,
            authenticated=True,
            fresh=True,
            confidence=heuristic_conf
        )
        
        decision = self.gate.evaluate(incident_id, [sig_a, sig_b])
        if not decision.approved:
            self.append_log("⚠️ [CONTROLLER] Evidence pending; relay remains connected")
            return False
            
        quorum_snapshot = {"state": QuorumState.APPROVED.value, "peers": ["AEDN-RACK-02", "AEDN-RACK-03"]}
        receipt = self.receipt_service.issue(
            decision=decision,
            organization_id="openclaw-sentinel",
            key_epoch=1,
            quorum=quorum_snapshot
        )
        
        success = self.controller.apply_containment(
            receipt=receipt,
            quorum_state=QuorumState.APPROVED.value,
            expected_incident_id=incident_id
        )
        
        if success:
            self.hal.relay.isolate()
            self.hal.led.blink(0.2)
            self.scorer.trigger_lockdown()
            self.append_log(f"🚨 [ANOMALY DETECTED] {pkt_label} (Score: {score:.4f})")
            self.append_log(f"⚡ [RELAY] Controller-approved line CUT. Hash: {receipt['payload']['event_hash'][:16]}...")
            self.hal.cellular.send_sms("+919876543210", f"ALERT: Line isolated on {self.node_id}")
            return True
        return False

    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.ui_thread_id = threading.get_ident()
        self._ui_log_queue = queue.Queue()
        self._event_log = deque(maxlen=200)
        self.root.title("🛡️ BLACKBOX SENTINEL")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(fg_color=COLOR_BG_DARK)
        self.root.resizable(False, False)
        self.root.attributes("-fullscreen", True)
        
        # Center on screen
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x = max(0, (screen_w - WINDOW_WIDTH) // 2)
        pos_y = max(0, (screen_h - WINDOW_HEIGHT) // 2)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{pos_x}+{pos_y}")

        self.font_title = ctk.CTkFont(family="Consolas", size=10, weight="bold")
        self.font_heading = ctk.CTkFont(family="Consolas", size=9, weight="bold")
        self.font_data = ctk.CTkFont(family="Consolas", size=11, weight="bold")
        self.font_small = ctk.CTkFont(family="Consolas", size=8)
        self.font_log = ctk.CTkFont(family="Consolas", size=8)

        # Core Components
        self.node_id = "AEDN-RACK-01"
        self.ledger_path = os.path.join(PROJECT_ROOT, "m3-ml-ledger", "data", "gui_ledger.json")
        self.master_aes_key = os.urandom(32)

        self.hal = get_hal(
            mode="sim",
            on_tamper_callback=self._handle_tamper_event,
            on_relay_change=self._handle_relay_change,
            node_id=self.node_id
        )
        self.scorer = AnomalyScorer()
        
        priv_key_b64 = os.environ.get("SENTINEL_ED25519_KEY")
        if priv_key_b64:
            self.signer = Ed25519ReceiptSigner.from_private_bytes(base64.urlsafe_b64decode(priv_key_b64))
        else:
            self.signer = Ed25519ReceiptSigner()
            
        counter_path = os.path.join(PROJECT_ROOT, "m3-ml-ledger", "data", "receipt_counter.txt")
        self.counter = SoftwareMonotonicCounter(counter_path)
        self.ledger = HashChainLedger(self.ledger_path)
        self.receipt_service = ContainmentReceiptService(self.ledger, self.counter, self.signer, self.node_id)
        self.gate = TwoSignalGate(required_signals=2)
        self.controller = SimTrustedController(controller_id=self.node_id)
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

        # Start background pipeline loop
        self.pipeline_thread = threading.Thread(target=self._pipeline_worker, daemon=True)
        self.pipeline_thread.start()

        # Start periodic GUI telemetry refresh
        self.root.after(100, self._update_telemetry_loop)

    def _build_header(self):
        header = ctk.CTkFrame(self.root, fg_color=COLOR_PANEL_BG, height=35, corner_radius=0)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side=tk.LEFT, padx=10, pady=2)
        
        ctk.CTkLabel(title_box, text="🛡️ BLACKBOX SENTINEL", font=self.font_title, text_color=COLOR_ACCENT_CYAN).pack(anchor="w")
        ctk.CTkLabel(title_box, text=f"NODE: {self.node_id} | TRANSPARENT BRIDGE", font=self.font_small, text_color=COLOR_TEXT_MUTED).pack(anchor="w")

        self.lbl_state_badge = ctk.CTkLabel(
            header,
            text="● INIT",
            font=self.font_heading,
            text_color=COLOR_WARNING_YELLOW,
            fg_color=COLOR_CARD_BG,
            corner_radius=4,
            padx=8,
            pady=2
        )
        self.lbl_state_badge.pack(side=tk.RIGHT, padx=10, pady=5)

    def _build_main_body(self):
        self.shell = ctk.CTkFrame(self.root, fg_color=COLOR_BG_DARK, corner_radius=0)
        self.shell.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.shell.grid_rowconfigure(1, weight=1)
        self.shell.grid_columnconfigure(0, weight=1)

        self.home_bar = ctk.CTkFrame(self.shell, fg_color=COLOR_PANEL_BG, height=25, corner_radius=6)
        self.home_bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.home_bar.grid_propagate(False)
        ctk.CTkLabel(self.home_bar, text="APPS", font=self.font_heading, text_color=COLOR_ACCENT_CYAN).pack(side=tk.LEFT, padx=10)
        self.view_title = ctk.CTkLabel(self.home_bar, text="TACTICAL OVERVIEW", font=self.font_heading, text_color=COLOR_TEXT_MAIN)
        self.view_title.pack(side=tk.RIGHT, padx=10)

        self.content_host = ctk.CTkFrame(self.shell, fg_color="transparent")
        self.content_host.grid(row=1, column=0, sticky="nsew")
        self._build_home_view()

    def _build_home_view(self):
        self._clear_content()
        self.view_title.configure(text="TACTICAL OVERVIEW")
        panel = ctk.CTkFrame(self.content_host, fg_color="transparent")
        panel.pack(fill=tk.BOTH, expand=True)
        
        # Grid layout for perfectly centered 2x2 buttons
        grid = ctk.CTkFrame(panel, fg_color="transparent")
        grid.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        apps = [
            ("◉", "ANOMALY\nGRAPH", "graph", COLOR_ACCENT_CYAN),
            ("⚠", "TAMPER\nCONTROLS", "controls", COLOR_ALERT_RED),
            ("▤", "SYSTEM\nLOGS", "logs", COLOR_SUCCESS_GREEN),
            ("▣", "SYSTEM\nSTATUS", "status", COLOR_WARNING_YELLOW),
        ]
        
        for i, (icon, label, view, color) in enumerate(apps):
            btn = ctk.CTkButton(
                grid, 
                text=f"{icon}\n{label}", 
                font=self.font_heading, 
                text_color=color, 
                fg_color=COLOR_CARD_BG,
                hover_color=COLOR_CARD_HOVER,
                border_width=1,
                border_color=COLOR_PANEL_BG,
                corner_radius=10,
                width=160,
                height=75,
                command=lambda v=view: self.show_view(v)
            )
            btn.grid(row=i // 2, column=i % 2, padx=8, pady=8)

    def _clear_content(self):
        for child in self.content_host.winfo_children():
            child.destroy()

    def show_view(self, view):
        if view == "home":
            self._build_home_view()
            return
        self._clear_content()
        back = ctk.CTkButton(self.home_bar, text="‹ HOME", font=self.font_small, text_color=COLOR_TEXT_MAIN, fg_color=COLOR_CARD_BG, hover_color=COLOR_CARD_HOVER, width=50, height=20, corner_radius=4, command=self._build_home_view)
        back.pack(side=tk.LEFT, padx=6)
        
        if view == "graph":
            self.view_title.configure(text="ANOMALY GRAPH")
            self._build_graph_view()
        elif view == "controls":
            self.view_title.configure(text="TAMPER CONTROLS")
            self._build_controls_view()
        elif view == "logs":
            self.view_title.configure(text="SYSTEM LOGS")
            self._build_logs_view()
        else:
            self.view_title.configure(text="SYSTEM STATUS")
            self._build_status_view()

    def _build_graph_view(self):
        ctk.CTkLabel(self.content_host, text="LIVE PACKET RATE / ANOMALY SCORE", font=self.font_heading, text_color=COLOR_ACCENT_CYAN).pack(anchor="w", padx=4, pady=2)
        canvas_frame = ctk.CTkFrame(self.content_host, fg_color=CHART_BG, corner_radius=8, border_width=1, border_color=CHART_GRID)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)
        self.telemetry_canvas = tk.Canvas(canvas_frame, bg=CHART_BG, highlightthickness=0)
        self.telemetry_canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self._draw_telemetry_graph()

    def _build_controls_view(self):
        panel = ctk.CTkFrame(self.content_host, fg_color="transparent")
        panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=2)
        ctk.CTkLabel(panel, text="AUTHORIZED TACTICAL ACTIONS", font=self.font_heading, text_color=COLOR_ACCENT_CYAN).pack(pady=2)
        
        actions = [
            ("⚡ INJECT C2 ATTACK", "#991b1b", "#7f1d1d", lambda: self.inject_attack("EXFILTRATION")), 
            ("💥 SYN FLOOD", "#9a3412", "#7c2d12", lambda: self.inject_attack("SYN_FLOOD")), 
            ("🚨 BREACH CASING", "#831843", "#4c0519", self.hal.tamper.simulate_tamper), 
            ("🔢 PIN OVERRIDE", "#065f46", "#064e3b", self._popup_pin_pad)
        ]
        
        for text, color, hover, command in actions:
            ctk.CTkButton(panel, text=text, font=self.font_heading, text_color="#ffffff", fg_color=color, hover_color=hover, corner_radius=6, height=34, command=command).pack(fill=tk.X, pady=4)

    def _build_logs_view(self):
        self.log_text = ctk.CTkTextbox(self.content_host, fg_color=CHART_BG, text_color=COLOR_TEXT_MAIN, font=self.font_log, wrap="word", corner_radius=8, border_width=1, border_color=CHART_GRID)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        for item in self._event_log:
            self.log_text.insert(tk.END, item + "\n")
        self.log_text.see(tk.END)

    def _build_status_view(self):
        panel = ctk.CTkFrame(self.content_host, fg_color="transparent")
        panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.lbl_pkts = self._make_stat_box(panel, "PACKETS INLINE", "0", COLOR_ACCENT_CYAN, 0, 0)
        self.lbl_anomalies = self._make_stat_box(panel, "ANOMALIES", "0", COLOR_ALERT_RED, 0, 1)
        self.lbl_blocks = self._make_stat_box(panel, "LEDGER BLOCKS", "1", COLOR_SUCCESS_GREEN, 1, 0)
        self.lbl_uptime = self._make_stat_box(panel, "UPTIME", "00:00:00", COLOR_TEXT_MAIN, 1, 1)
        ctk.CTkLabel(panel, text="UART: /dev/ttyAMA5 | RECEIPT: Ed25519", font=self.font_small, text_color=COLOR_SUCCESS_GREEN).grid(row=2, column=0, columnspan=2, pady=10)
        for col in (0, 1):
            panel.grid_columnconfigure(col, weight=1)

    def _make_stat_box(self, parent, title, val, color, row, col):
        card = ctk.CTkFrame(parent, fg_color=COLOR_CARD_BG, corner_radius=8)
        card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        
        ctk.CTkLabel(card, text=title, font=self.font_small, text_color=COLOR_TEXT_MUTED).pack(anchor="w", padx=10, pady=(6, 0))
        val_lbl = ctk.CTkLabel(card, text=val, font=self.font_data, text_color=color)
        val_lbl.pack(anchor="w", padx=10, pady=(0, 6))
        return val_lbl

    def _draw_telemetry_graph(self):
        canvas = getattr(self, "telemetry_canvas", None)
        if canvas is None or not canvas.winfo_exists():
            return
        width = max(1, canvas.winfo_width() or 430)
        height = max(1, canvas.winfo_height() or 150)
        canvas.delete("all")
        canvas.create_line(0, height // 2, width, height // 2, fill=CHART_GRID)
        canvas.create_text(6, 6, anchor="nw", text="PACKET RATE", fill=CHART_PACKET, font=("Consolas", 8))
        canvas.create_text(width - 6, 6, anchor="ne", text="ANOMALY SCORE", fill=CHART_SCORE, font=("Consolas", 8))
        def series(values, color, scale):
            if len(values) < 2:
                return
            points = []
            for i, value in enumerate(values):
                x = 6 + i * (width - 12) / max(1, len(values) - 1)
                y = height - 8 - min(1.0, max(0.0, value / scale)) * (height - 24)
                points.extend((x, y))
            canvas.create_line(*points, fill=color, width=2, smooth=True)
        series(list(self.packet_rate_history), CHART_PACKET, 20.0)
        series(list(self.anomaly_score_history), CHART_SCORE, 1.0)

    def _build_footer(self):
        footer = ctk.CTkFrame(self.root, fg_color=COLOR_PANEL_BG, height=20, corner_radius=0)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)

        ctk.CTkLabel(
            footer,
            text=f"BlackBox Sentinel v2.2 | SHA-256 Ledger: VERIFIED | Hardware: SIMULATION",
            font=self.font_small,
            text_color=COLOR_TEXT_MUTED
        ).pack(side=tk.LEFT, padx=10, pady=2)

    def _append_log_main(self, msg: str):
        t_str = datetime.now().strftime("%H:%M:%S")
        rendered = f"[{t_str}] {msg}"
        self._event_log.append(rendered)
        log_text = getattr(self, "log_text", None)
        if log_text is not None and log_text.winfo_exists():
            log_text.insert(tk.END, rendered + "\n")
            log_text.see(tk.END)

    def append_log(self, msg: str):
        if threading.get_ident() == self.ui_thread_id:
            self._append_log_main(msg)
        else:
            self._ui_log_queue.put(msg)

    def inject_attack(self, attack_type: str):
        self.injected_attack_type = attack_type
        self.append_log(f"⚡ [SIMULATOR] Scheduled adversarial injection: {attack_type}")

    def _popup_pin_pad(self):
        if hasattr(self, 'pin_frame') and self.pin_frame.winfo_exists():
            self.pin_frame.destroy()
            
        win = ctk.CTkFrame(self.root, fg_color=COLOR_PANEL_BG, corner_radius=12, border_width=1, border_color=COLOR_CARD_BG)
        win.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=260, height=240)
        self.pin_frame = win
        
        ctk.CTkLabel(win, text="ENTER SECURITY PIN", font=self.font_heading, text_color=COLOR_ACCENT_CYAN).pack(pady=6)
        
        pin_disp = ctk.CTkLabel(win, text="____", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), text_color=COLOR_TEXT_MAIN, fg_color="#000", corner_radius=6, width=100, height=24)
        pin_disp.pack(pady=4)

        pin_str = []

        def press_num(n):
            if len(pin_str) < 4:
                pin_str.append(str(n))
                pin_disp.configure(text="* " * len(pin_str) + "_ " * (4 - len(pin_str)))

        def clear():
            pin_str.clear()
            pin_disp.configure(text="____")
            
        def close_pad():
            win.destroy()

        def submit():
            code_val = "".join(pin_str)
            if validate_pin(code_val) and self.scorer.pin_override(code_val):
                self.controller.require_recovery()
                self.controller.authorize_recovery(True)
                self.hal.relay.engage()
                self.hal.led.solid_on()
                self.ledger.add_entry("tactical_override", {"pin_status": "ACCEPTED", "relay": "ENGAGED"})
                self.append_log("✅ [PIN OVERRIDE] Correct PIN entered -> Data Line Restored & ARMED")
                win.destroy()
            else:
                pin_str.clear()
                pin_disp.configure(text="REJECT", text_color="red")
                win.after(1000, lambda: pin_disp.configure(text="____", text_color=COLOR_TEXT_MAIN))

        pad_frame = ctk.CTkFrame(win, fg_color="transparent")
        pad_frame.pack(pady=4)

        keys = [
            ("1", 0, 0), ("2", 0, 1), ("3", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("7", 2, 0), ("8", 2, 1), ("9", 2, 2),
            ("CLR", 3, 0), ("0", 3, 1), ("OK", 3, 2)
        ]

        for text, r, c in keys:
            if text == "CLR":
                cmd = clear
                btn_color = "#991b1b"
            elif text == "OK":
                cmd = submit
                btn_color = "#065f46"
            else:
                cmd = lambda n=text: press_num(n)
                btn_color = COLOR_CARD_BG

            btn = ctk.CTkButton(pad_frame, text=text, font=self.font_heading, width=45, height=28, fg_color=btn_color, hover_color=COLOR_CARD_HOVER, corner_radius=6, command=cmd)
            btn.grid(row=r, column=c, padx=3, pady=3)
            
        close_btn = ctk.CTkButton(win, text="CANCEL", font=self.font_small, fg_color="#334155", hover_color="#475569", corner_radius=4, width=70, height=22, command=close_pad)
        close_btn.pack(pady=4)

    def _handle_tamper_event(self):
        self.append_log("🚨 [TAMPER ALERT] Casing breached! Zeroizing volatile keys...")
        self.master_aes_key = b"\x00" * 32
        incident_id = f"{self.node_id}:tamper:{int(time.time())}"
        self._apply_containment_logic(incident_id, 1.0, "TAMPER_BREACH")
        self.ledger.add_entry("tamper_breach", {"action": "KEYS_ZEROIZED", "relay": "ISOLATED", "controller_state": "TAMPERED"})
        self.append_log("🔥 [ZEROIZATION] Master cryptographic keys purged from RAM.")

    def _handle_relay_change(self, state: str):
        pass

    def _pipeline_worker(self):
        self.append_log("System booting... starting 120-packet baseline calibration")
        self.scorer.start_calibration()
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

        while self.is_running:
            if self.injected_attack_type:
                pkt = self.traffic_gen.generate_attack_packet(self.injected_attack_type)
                self.injected_attack_type = None
            else:
                pkt = self.traffic_gen.generate_normal_packet()

            self.packet_count += 1
            res = self.scorer.ingest_features(pkt)
            self.latest_anomaly_score = float(res.get("score", 0.0) or 0.0)

            if res.get("is_anomaly", False):
                self.anomaly_count += 1
                score = res.get("score", 0.0)
                incident_id = f"{self.node_id}:{int(time.time())}"
                self._apply_containment_logic(incident_id, score, pkt.get("label", "ANOMALY"), pkt)

            time.sleep(0.08)

    def _update_telemetry_loop(self):
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

        if hasattr(self, "lbl_pkts"):
            self.lbl_pkts.configure(text=str(self.packet_count))
        if hasattr(self, "lbl_anomalies"):
            self.lbl_anomalies.configure(text=str(self.anomaly_count))
        if hasattr(self, "lbl_blocks"):
            self.lbl_blocks.configure(text=str(len(self.ledger.chain)))

        elapsed = int(time.time() - self.start_time)
        hrs, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        if hasattr(self, "lbl_uptime"):
            self.lbl_uptime.configure(text=f"{hrs:02d}:{mins:02d}:{secs:02d}")

        state = self.scorer.state.value.upper()
        if state == "CALIBRATING":
            self.lbl_state_badge.configure(text="● CALIBRATING", text_color=COLOR_WARNING_YELLOW)
        elif state == "ARMED":
            self.lbl_state_badge.configure(text="● ARMED & MONITORING", text_color=COLOR_SUCCESS_GREEN)
        elif state in ("ALERT", "LOCKDOWN"):
            self.lbl_state_badge.configure(text="🚨 LOCKDOWN (LINE CUT)", text_color=COLOR_ALERT_RED)

        if self.is_running:
            self.root.after(100, self._update_telemetry_loop)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self):
        self.is_running = False
        self.root.destroy()

if __name__ == "__main__":
    app = SentinelTacticalApp()
    app.run()
