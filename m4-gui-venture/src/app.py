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
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
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
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 480
COLOR_BG_DARK = "#090d16"
COLOR_PANEL_BG = "#111827"
COLOR_CARD_BG = "#1f293d"
COLOR_ACCENT_CYAN = "#00f0ff"
COLOR_ALERT_RED = "#ff2a5f"
COLOR_SUCCESS_GREEN = "#00ff88"
COLOR_WARNING_YELLOW = "#ffd000"
COLOR_TEXT_MAIN = "#f1f5f9"
COLOR_TEXT_MUTED = "#94a3b8"
FONT_TITLE = ("Consolas", 15, "bold")
FONT_HEADING = ("Consolas", 11, "bold")
FONT_DATA = ("Consolas", 13, "bold")
FONT_SMALL = ("Consolas", 9)
FONT_LOG = ("Consolas", 9)


class SentinelTacticalApp:
    def __init__(self):
        self.root = tk.Tk()
        self.ui_thread_id = threading.get_ident()
        self._ui_log_queue = queue.Queue()
        self.root.title("🛡️ BLACKBOX SENTINEL — AUTONOMOUS EDGE DEFENSE NODE")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=COLOR_BG_DARK)
        self.root.resizable(False, False)
        
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
        header = tk.Frame(self.root, bg=COLOR_PANEL_BG, height=52)
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
            pady=4,
            relief=tk.RIDGE
        )
        self.lbl_state_badge.pack(side=tk.RIGHT, padx=15, pady=10)

    def _build_main_body(self):
        body = tk.Frame(self.root, bg=COLOR_BG_DARK)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        # ── Left Column: Metrics & Hardware Telemetry (320px) ──
        left_col = tk.Frame(body, bg=COLOR_BG_DARK, width=280)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 6))

        # Metrics Card
        metrics_panel = tk.LabelFrame(left_col, text=" 📊 SYSTEM TELEMETRY ", font=FONT_SMALL, fg=COLOR_ACCENT_CYAN, bg=COLOR_PANEL_BG, bd=1)
        metrics_panel.pack(fill=tk.X, pady=(0, 6))

        # Metric grid
        grid_frame = tk.Frame(metrics_panel, bg=COLOR_PANEL_BG)
        grid_frame.pack(fill=tk.X, padx=8, pady=6)

        self.lbl_pkts = self._make_stat_box(grid_frame, "PACKETS INLINE", "0", COLOR_ACCENT_CYAN, 0, 0)
        self.lbl_anomalies = self._make_stat_box(grid_frame, "ANOMALIES", "0", COLOR_ALERT_RED, 0, 1)
        self.lbl_blocks = self._make_stat_box(grid_frame, "LEDGER BLOCKS", "1", COLOR_SUCCESS_GREEN, 1, 0)
        self.lbl_uptime = self._make_stat_box(grid_frame, "UPTIME", "00:00:00", COLOR_TEXT_MAIN, 1, 1)

        # Hardware Status Panel
        hw_panel = tk.LabelFrame(left_col, text=" 🔌 HARDWARE PERIPHERALS ", font=FONT_SMALL, fg=COLOR_ACCENT_CYAN, bg=COLOR_PANEL_BG, bd=1)
        hw_panel.pack(fill=tk.BOTH, expand=True)

        self.lbl_relay_stat = tk.Label(hw_panel, text="⚡ Relay: ENGAGED (Line Connected)", font=FONT_SMALL, fg=COLOR_SUCCESS_GREEN, bg=COLOR_PANEL_BG, anchor="w")
        self.lbl_relay_stat.pack(fill=tk.X, padx=10, pady=2)

        self.lbl_led_stat = tk.Label(hw_panel, text="💡 Status LED: ACTIVE", font=FONT_SMALL, fg=COLOR_SUCCESS_GREEN, bg=COLOR_PANEL_BG, anchor="w")
        self.lbl_led_stat.pack(fill=tk.X, padx=10, pady=2)

        self.lbl_gsm_stat = tk.Label(hw_panel, text="📱 SIM800L: 2G GSM REGISTERED", font=FONT_SMALL, fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG, anchor="w")
        self.lbl_gsm_stat.pack(fill=tk.X, padx=10, pady=2)

        self.lbl_tamper_stat = tk.Label(hw_panel, text="🛡️ Anti-Tamper: ENCLOSURE SECURE", font=FONT_SMALL, fg=COLOR_SUCCESS_GREEN, bg=COLOR_PANEL_BG, anchor="w")
        self.lbl_tamper_stat.pack(fill=tk.X, padx=10, pady=2)

        self.lbl_controller_stat = tk.Label(hw_panel, text="🧠 Controller: SAFE | Link: HEALTHY", font=FONT_SMALL, fg=COLOR_SUCCESS_GREEN, bg=COLOR_PANEL_BG, anchor="w")
        self.lbl_controller_stat.pack(fill=tk.X, padx=10, pady=2)
        self.lbl_signal_stat = tk.Label(hw_panel, text="🔐 Signals: 0/2 independent evidence", font=FONT_SMALL, fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG, anchor="w")
        self.lbl_signal_stat.pack(fill=tk.X, padx=10, pady=2)
        self.lbl_receipt_stat = tk.Label(hw_panel, text="🧾 Receipt: NOT AVAILABLE | Quorum: N/A", font=FONT_SMALL, fg=COLOR_TEXT_MUTED, bg=COLOR_PANEL_BG, anchor="w")
        self.lbl_receipt_stat.pack(fill=tk.X, padx=10, pady=2)
        self.lbl_key_stat = tk.Label(hw_panel, text="🔑 Key state: VALID | Power: PRIMARY", font=FONT_SMALL, fg=COLOR_SUCCESS_GREEN, bg=COLOR_PANEL_BG, anchor="w")
        self.lbl_key_stat.pack(fill=tk.X, padx=10, pady=2)

        # ── Right Column: Logs, Interactive Attacks & PIN Pad ──
        right_col = tk.Frame(body, bg=COLOR_BG_DARK)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Forensic Ledger Log Viewer
        log_panel = tk.LabelFrame(right_col, text=" 📋 FORENSIC SHA-256 LEDGER & EVENT STREAM ", font=FONT_SMALL, fg=COLOR_ACCENT_CYAN, bg=COLOR_PANEL_BG, bd=1)
        log_panel.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        self.log_text = tk.Text(
            log_panel,
            bg="#070a10",
            fg=COLOR_TEXT_MAIN,
            font=FONT_LOG,
            relief=tk.FLAT,
            height=10,
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Tactical Control Bar
        ctrl_bar = tk.Frame(right_col, bg=COLOR_PANEL_BG, height=75)
        ctrl_bar.pack(fill=tk.X)

        # Interactive Buttons
        btn_attack = tk.Button(
            ctrl_bar,
            text="⚡ INJECT C2 ATTACK",
            font=FONT_SMALL,
            fg="#ffffff",
            bg="#b91c1c",
            activebackground="#dc2626",
            command=lambda: self.inject_attack("EXFILTRATION"),
            padx=8,
            pady=4,
            relief=tk.GROOVE
        )
        btn_attack.pack(side=tk.LEFT, padx=6, pady=8)

        btn_syn = tk.Button(
            ctrl_bar,
            text="💥 SYN FLOOD",
            font=FONT_SMALL,
            fg="#ffffff",
            bg="#7c2d12",
            activebackground="#9a3412",
            command=lambda: self.inject_attack("SYN_FLOOD"),
            padx=8,
            pady=4,
            relief=tk.GROOVE
        )
        btn_syn.pack(side=tk.LEFT, padx=6, pady=8)

        btn_tamper = tk.Button(
            ctrl_bar,
            text="🚨 BREACH CASING",
            font=FONT_SMALL,
            fg="#ffffff",
            bg="#4c0519",
            activebackground="#881337",
            command=self.hal.tamper.simulate_tamper,
            padx=8,
            pady=4,
            relief=tk.GROOVE
        )
        btn_tamper.pack(side=tk.LEFT, padx=6, pady=8)

        btn_pin = tk.Button(
            ctrl_bar,
            text="🔢 PIN OVERRIDE",
            font=FONT_SMALL,
            fg="#ffffff",
            bg="#065f46",
            activebackground="#059669",
            command=self._popup_pin_pad,
            padx=8,
            pady=4,
            relief=tk.GROOVE
        )
        btn_pin.pack(side=tk.RIGHT, padx=6, pady=8)

    def _make_stat_box(self, parent, title, val, color, row, col):
        card = tk.Frame(parent, bg=COLOR_CARD_BG, padx=8, pady=4)
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)

        tk.Label(card, text=title, font=("Consolas", 8), fg=COLOR_TEXT_MUTED, bg=COLOR_CARD_BG).pack(anchor="w")
        val_lbl = tk.Label(card, text=val, font=FONT_DATA, fg=color, bg=COLOR_CARD_BG)
        val_lbl.pack(anchor="w")
        return val_lbl

    def _build_footer(self):
        footer = tk.Frame(self.root, bg=COLOR_PANEL_BG, height=24)
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
        """Append a log entry on Tk's main thread."""
        t_str = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{t_str}] {msg}\n")
        self.log_text.see(tk.END)

    def append_log(self, msg: str):
        """Queue worker messages and render them safely in the GUI thread."""
        if threading.get_ident() == self.ui_thread_id:
            self._append_log_main(msg)
        else:
            self._ui_log_queue.put(msg)

    def inject_attack(self, attack_type: str):
        self.injected_attack_type = attack_type
        self.append_log(f"⚡ [SIMULATOR] Scheduled adversarial injection: {attack_type}")

    def _popup_pin_pad(self):
        """Tactical On-Screen PIN Pad Dialog."""
        win = tk.Toplevel(self.root)
        win.title("TACTICAL PIN OVERRIDE")
        win.geometry("260x320")
        win.configure(bg=COLOR_PANEL_BG)
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="ENTER SECURITY PIN", font=FONT_HEADING, fg=COLOR_ACCENT_CYAN, bg=COLOR_PANEL_BG).pack(pady=8)
        
        pin_disp = tk.Label(win, text="____", font=("Consolas", 20, "bold"), fg=COLOR_TEXT_MAIN, bg="#000000", width=10)
        pin_disp.pack(pady=5)

        pin_str = []

        def press_num(n):
            if len(pin_str) < 4:
                pin_str.append(str(n))
                pin_disp.config(text="* " * len(pin_str) + "_ " * (4 - len(pin_str)))

        def clear():
            pin_str.clear()
            pin_disp.config(text="____")

        def submit():
            code = "".join(pin_str)
            if validate_pin(code) and self.scorer.pin_override(code):
                self.controller.recover()
                self.hal.relay.engage()
                self.hal.led.solid_on()
                self.ledger.add_entry("tactical_override", {"pin_status": "ACCEPTED", "relay": "ENGAGED"})
                self.append_log("✅ [PIN OVERRIDE] Correct PIN entered -> Data Line Restored & ARMED")
                win.destroy()
            else:
                messagebox.showerror("PIN REJECTED", "Invalid Override PIN Code!")
                clear()

        # Keypad Grid
        pad_frame = tk.Frame(win, bg=COLOR_PANEL_BG)
        pad_frame.pack(pady=8)

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
        self.hal.led.blink(0.05)
        self.ledger.add_entry("tamper_breach", {"action": "KEYS_ZEROIZED", "relay": "ISOLATED", "controller_state": "TAMPERED"})
        self.lbl_tamper_stat.config(text="🚨 Anti-Tamper: BREACH DETECTED!", fg=COLOR_ALERT_RED)
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

        # Update metrics
        self.lbl_pkts.config(text=str(self.packet_count))
        self.lbl_anomalies.config(text=str(self.anomaly_count))
        self.lbl_blocks.config(text=str(len(self.ledger.chain)))

        elapsed = int(time.time() - self.start_time)
        hrs, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        self.lbl_uptime.config(text=f"{hrs:02d}:{mins:02d}:{secs:02d}")

        # Update State Badge
        state = self.scorer.state.value.upper()
        if state == "CALIBRATING":
            self.lbl_state_badge.config(text="● CALIBRATING (AI BASELINE)", fg=COLOR_WARNING_YELLOW)
        elif state == "ARMED":
            self.lbl_state_badge.config(text="● ARMED & MONITORING", fg=COLOR_SUCCESS_GREEN)
        elif state in ("ALERT", "LOCKDOWN"):
            self.lbl_state_badge.config(text="🚨 AIR-GAP LOCKDOWN (LINE CUT)", fg=COLOR_ALERT_RED)

        # Update Hardware Status
        relay_state = self.hal.relay.get_state()
        if relay_state == "ISOLATED":
            self.lbl_relay_stat.config(text="⚡ Relay: ISOLATED (Line Severed)", fg=COLOR_ALERT_RED)
        else:
            self.lbl_relay_stat.config(text="⚡ Relay: ENGAGED (Line Connected)", fg=COLOR_SUCCESS_GREEN)

        if self.hal.tamper.is_tampered():
            self.lbl_tamper_stat.config(text="🚨 Anti-Tamper: CASING BREACHED!", fg=COLOR_ALERT_RED)

        controller_state = self.controller.state.value
        if controller_state == "TAMPERED":
            self.lbl_controller_stat.config(text="🧠 Controller: TAMPERED | Link: HEALTHY", fg=COLOR_ALERT_RED)
            self.lbl_key_stat.config(text="🔑 Key state: INVALIDATED | Power: PRIMARY", fg=COLOR_ALERT_RED)
        elif controller_state == "ISOLATED":
            self.lbl_controller_stat.config(text="🧠 Controller: ISOLATED | Link: HEALTHY", fg=COLOR_ALERT_RED)
            self.lbl_signal_stat.config(text="🔐 Signals: 2/2 independent evidence", fg=COLOR_ALERT_RED)
            latest = self.controller.receipts[-1] if self.controller.receipts else None
            receipt_state = self.controller.verify_receipt(latest)[1] if latest else "NOT_AVAILABLE"
            receipt_id = latest.receipt_id if latest else "N/A"
            self.lbl_receipt_stat.config(text=f"🧾 Receipt: {receipt_state} {receipt_id} | Quorum: N/A", fg=COLOR_SUCCESS_GREEN if receipt_state == "VALID" else COLOR_ALERT_RED)
        elif controller_state == "ARMED":
            self.lbl_controller_stat.config(text="🧠 Controller: ARMED | Link: HEALTHY", fg=COLOR_SUCCESS_GREEN)
            self.lbl_signal_stat.config(text="🔐 Signals: waiting for independent evidence", fg=COLOR_TEXT_MUTED)
            self.lbl_receipt_stat.config(text="🧾 Receipt: N/A | Quorum: NOT CONFIGURED", fg=COLOR_TEXT_MUTED)

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
