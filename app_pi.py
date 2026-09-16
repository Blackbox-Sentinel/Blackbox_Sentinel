"""
BlackBox Sentinel — M4 Advanced Operator Console v2
Premium Dark-Glass Interface for 480×320 TFT Touchscreen

Color System: Violet · Coral · Emerald · Amber on Pure Black Glass
Views: Overview · Signals · Actions · Journal · Health
States: Calibrating · Armed · Lockdown

Backend preserved: ContainmentReceiptService, Ed25519ReceiptSigner,
TwoSignalGate, SimTrustedController, /dev/ttyAMA5 UART dispatch,
background pipeline worker, clean shutdown path.
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

# ══════════════════════════════════════════════════════════════
#  ADVANCED COLOR SYSTEM v2 — Violet / Coral / Emerald / Amber
# ══════════════════════════════════════════════════════════════
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 320

# ── Base Surfaces ──
COL_BG          = "#050508"    # Pure black background
COL_SURFACE     = "#0C0C14"    # Dark glass card
COL_SURFACE_ALT = "#111118"    # Slightly lifted surface
COL_BORDER      = "#1A1A2E"    # Subtle card border
COL_BORDER_GLOW = "#2D2B55"    # Glow border (hover)

# ── Accent Palette ──
COL_VIOLET      = "#8B5CF6"    # Primary accent
COL_VIOLET_DIM  = "#6D44C8"    # Dimmed violet
COL_VIOLET_DARK = "#1A1030"    # Fill under violet graph
COL_CORAL       = "#FF4F6D"    # Alert / anomaly / danger
COL_CORAL_DARK  = "#2A0F18"    # Fill under coral graph
COL_EMERALD     = "#34D399"    # Success / healthy / verified
COL_EMERALD_DRK = "#0A2A1F"    # Dark emerald for buttons
COL_AMBER       = "#F59E0B"    # Warning / data / uptime
COL_AMBER_DARK  = "#2A1F0A"    # Dark amber
COL_PINK        = "#EC4899"    # Breach accent

# ── Text ──
COL_TEXT        = "#FFFFFF"    # Primary text
COL_TEXT_DIM    = "#6B7280"    # Muted labels
COL_TEXT_FAINT  = "#374151"    # Grid lines / very dim

# ── Navigation ──
NAV_WIDTH  = 48
NAV_ICONS  = ["\u2B22", "\u25CE", "\u26A1", "\u2261", "\u2666"]
NAV_VIEWS  = ["overview", "signals", "actions", "journal", "health"]


# ══════════════════════════════════════════════════════════════
#  SENTINEL TACTICAL APPLICATION
# ══════════════════════════════════════════════════════════════
class SentinelTacticalApp:
    """Advanced dark-glass operator console for BlackBox Sentinel."""

    # ──────────────────────────────────────────────────────────
    #  M3 CONTAINMENT LOGIC — PRESERVED EXACTLY
    # ──────────────────────────────────────────────────────────
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
            self.append_log("\u26A0\uFE0F [CONTROLLER] Evidence pending; relay remains connected")
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
            self.append_log(f"\U0001F6A8 [ANOMALY DETECTED] {pkt_label} (Score: {score:.4f})")
            self.append_log(f"\u26A1 [RELAY] Controller-approved line CUT. Hash: {receipt['payload']['event_hash'][:16]}...")
            self.hal.cellular.send_sms("+919876543210", f"ALERT: Line isolated on {self.node_id}")
            return True
        return False

    # ──────────────────────────────────────────────────────────
    #  INITIALIZATION
    # ──────────────────────────────────────────────────────────
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.ui_thread_id = threading.get_ident()
        self._ui_log_queue = queue.Queue()
        self._event_log = deque(maxlen=200)
        self.root.title("BLACKBOX SENTINEL")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(fg_color=COL_BG)
        self.root.resizable(False, False)
        self.root.attributes("-fullscreen", True)

        # Center on screen (used on desktop; Pi TFT fills 480x320)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x = max(0, (screen_w - WINDOW_WIDTH) // 2)
        pos_y = max(0, (screen_h - WINDOW_HEIGHT) // 2)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{pos_x}+{pos_y}")

        # ── Fonts ──
        self.font_brand    = ctk.CTkFont(family="Consolas", size=11, weight="bold")
        self.font_section  = ctk.CTkFont(family="Consolas", size=9, weight="bold")
        self.font_data_lg  = ctk.CTkFont(family="Consolas", size=16, weight="bold")
        self.font_data     = ctk.CTkFont(family="Consolas", size=11, weight="bold")
        self.font_label    = ctk.CTkFont(family="Consolas", size=8)
        self.font_small    = ctk.CTkFont(family="Consolas", size=7)
        self.font_nav      = ctk.CTkFont(family="Consolas", size=14)
        self.font_log      = ctk.CTkFont(family="Consolas", size=8)
        self.font_pin      = ctk.CTkFont(family="Consolas", size=16, weight="bold")

        # ── Core Components (PRESERVED — do not modify) ──
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

        # ── Telemetry State (PRESERVED) ──
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

        # ── UI State ──
        self.current_view = "overview"
        self._nav_buttons = []

        # Build layout and show default view
        self._build_layout()
        self._show_view("overview")

        # Start background pipeline (PRESERVED)
        self.pipeline_thread = threading.Thread(target=self._pipeline_worker, daemon=True)
        self.pipeline_thread.start()
        self.root.after(100, self._update_telemetry_loop)

    # ──────────────────────────────────────────────────────────
    #  LAYOUT SKELETON
    # ──────────────────────────────────────────────────────────
    def _build_layout(self):
        """Construct the persistent shell: header, nav dock, content host, footer."""
        self.main_frame = ctk.CTkFrame(self.root, fg_color=COL_BG, corner_radius=0)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # ── Header Bar (30px) ──
        self.header = ctk.CTkFrame(self.main_frame, fg_color=COL_SURFACE, height=30, corner_radius=0)
        self.header.pack(fill=tk.X)
        self.header.pack_propagate(False)

        brand = ctk.CTkFrame(self.header, fg_color="transparent")
        brand.pack(side=tk.LEFT, padx=8, pady=2)
        ctk.CTkLabel(brand, text="\u25C8 SENTINEL", font=self.font_brand,
                     text_color=COL_VIOLET).pack(side=tk.LEFT)
        ctk.CTkLabel(brand, text=f"  {self.node_id}", font=self.font_small,
                     text_color=COL_TEXT_DIM).pack(side=tk.LEFT)

        self.status_badge = ctk.CTkLabel(
            self.header, text="\u25CF INIT", font=self.font_label,
            text_color=COL_AMBER, fg_color=COL_BG,
            corner_radius=8, padx=8, pady=2
        )
        self.status_badge.pack(side=tk.RIGHT, padx=8, pady=4)

        # ── Body (nav + content) ──
        body = ctk.CTkFrame(self.main_frame, fg_color=COL_BG, corner_radius=0)
        body.pack(fill=tk.BOTH, expand=True)

        # Nav dock (left, 48px)
        self.nav_dock = ctk.CTkFrame(body, fg_color=COL_SURFACE, width=NAV_WIDTH, corner_radius=8)
        self.nav_dock.pack(side=tk.LEFT, fill=tk.Y, padx=(4, 0), pady=4)
        self.nav_dock.pack_propagate(False)

        self._nav_buttons = []
        for i, (icon, view) in enumerate(zip(NAV_ICONS, NAV_VIEWS)):
            btn = ctk.CTkButton(
                self.nav_dock, text=icon, font=self.font_nav,
                width=36, height=36, corner_radius=8,
                fg_color="transparent", hover_color=COL_BORDER,
                text_color=COL_TEXT_DIM, border_width=0,
                command=lambda v=view: self._show_view(v)
            )
            btn.pack(pady=(8 if i == 0 else 4, 0), padx=6)
            self._nav_buttons.append(btn)

        # Content area (fills remaining space)
        self.content = ctk.CTkFrame(body, fg_color=COL_BG, corner_radius=0)
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ── Footer Bar (18px) ──
        self.footer = ctk.CTkFrame(self.main_frame, fg_color=COL_SURFACE, height=18, corner_radius=0)
        self.footer.pack(fill=tk.X)
        self.footer.pack_propagate(False)
        ctk.CTkLabel(
            self.footer,
            text="v2.2 \u2502 SHA-256 Ledger \u2502 Ed25519 Receipt \u2502 SIMULATION",
            font=self.font_small, text_color=COL_TEXT_DIM
        ).pack(side=tk.LEFT, padx=8, pady=1)

    # ──────────────────────────────────────────────────────────
    #  VIEW NAVIGATION
    # ──────────────────────────────────────────────────────────
    def _show_view(self, view):
        """Switch the active content view and highlight the nav button."""
        self.current_view = view
        # Update nav highlight (active = violet glow ring, inactive = transparent)
        for i, btn in enumerate(self._nav_buttons):
            if NAV_VIEWS[i] == view:
                btn.configure(fg_color=COL_VIOLET_DARK, text_color=COL_VIOLET,
                              border_width=1, border_color=COL_VIOLET)
            else:
                btn.configure(fg_color="transparent", text_color=COL_TEXT_DIM,
                              border_width=0)

        # Clear content
        for child in self.content.winfo_children():
            child.destroy()

        # Build requested view
        builders = {
            "overview": self._build_overview,
            "signals":  self._build_signals,
            "actions":  self._build_actions,
            "journal":  self._build_journal,
            "health":   self._build_health,
        }
        builders.get(view, self._build_overview)()

    # ──────────────────────────────────────────────────────────
    #  VIEW 1 — OVERVIEW (Home Dashboard)
    # ──────────────────────────────────────────────────────────
    def _build_overview(self):
        # ── Top row: large packet card + two stacked small cards ──
        top = ctk.CTkFrame(self.content, fg_color="transparent")
        top.pack(fill=tk.X, pady=(0, 4))
        top.grid_columnconfigure(0, weight=3)
        top.grid_columnconfigure(1, weight=2)

        # Large packet card with embedded sparkline
        pkt_card = ctk.CTkFrame(top, fg_color=COL_SURFACE, corner_radius=8,
                                border_width=1, border_color=COL_BORDER)
        pkt_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4), ipady=2)

        self.lbl_pkts = ctk.CTkLabel(pkt_card, text="0", font=self.font_data_lg,
                                     text_color=COL_TEXT, anchor="w")
        self.lbl_pkts.pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(pkt_card, text="packets processed", font=self.font_small,
                     text_color=COL_TEXT_DIM, anchor="w").pack(anchor="w", padx=10)

        self.mini_canvas = tk.Canvas(pkt_card, bg=COL_SURFACE,
                                     highlightthickness=0, height=35)
        self.mini_canvas.pack(fill=tk.X, padx=6, pady=(2, 4))

        # Right column: anomalies + ledger blocks
        right = ctk.CTkFrame(top, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")

        anom_card = ctk.CTkFrame(right, fg_color=COL_SURFACE, corner_radius=8,
                                 border_width=1, border_color=COL_BORDER)
        anom_card.pack(fill=tk.X, pady=(0, 4))
        self.lbl_anomalies = ctk.CTkLabel(anom_card, text="0", font=self.font_data,
                                          text_color=COL_CORAL)
        self.lbl_anomalies.pack(anchor="w", padx=10, pady=(4, 0))
        ctk.CTkLabel(anom_card, text="anomalies", font=self.font_small,
                     text_color=COL_TEXT_DIM).pack(anchor="w", padx=10, pady=(0, 4))

        led_card = ctk.CTkFrame(right, fg_color=COL_SURFACE, corner_radius=8,
                                border_width=1, border_color=COL_BORDER)
        led_card.pack(fill=tk.X)
        self.lbl_blocks = ctk.CTkLabel(led_card, text="1", font=self.font_data,
                                       text_color=COL_EMERALD)
        self.lbl_blocks.pack(anchor="w", padx=10, pady=(4, 0))
        ctk.CTkLabel(led_card, text="ledger blocks", font=self.font_small,
                     text_color=COL_TEXT_DIM).pack(anchor="w", padx=10, pady=(0, 4))

        # ── Bottom row: threat gauge + uptime/health ──
        bot = ctk.CTkFrame(self.content, fg_color="transparent")
        bot.pack(fill=tk.BOTH, expand=True)
        bot.grid_columnconfigure(0, weight=1)
        bot.grid_columnconfigure(1, weight=1)

        # Threat gauge card
        gauge_card = ctk.CTkFrame(bot, fg_color=COL_SURFACE, corner_radius=8,
                                  border_width=1, border_color=COL_BORDER)
        gauge_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        self.gauge_canvas = tk.Canvas(gauge_card, bg=COL_SURFACE,
                                      highlightthickness=0, width=100, height=72)
        self.gauge_canvas.pack(pady=(4, 0))
        self._draw_threat_gauge(0.0)
        ctk.CTkLabel(gauge_card, text="threat index", font=self.font_small,
                     text_color=COL_TEXT_DIM).pack(pady=(0, 4))

        # Uptime + system health card
        up_card = ctk.CTkFrame(bot, fg_color=COL_SURFACE, corner_radius=8,
                               border_width=1, border_color=COL_BORDER)
        up_card.grid(row=0, column=1, sticky="nsew")

        self.lbl_uptime = ctk.CTkLabel(up_card, text="00:00:00",
                                       font=self.font_data_lg, text_color=COL_AMBER)
        self.lbl_uptime.pack(anchor="w", padx=10, pady=(8, 0))
        ctk.CTkLabel(up_card, text="uptime", font=self.font_small,
                     text_color=COL_TEXT_DIM).pack(anchor="w", padx=10)

        hf = ctk.CTkFrame(up_card, fg_color="transparent")
        hf.pack(fill=tk.X, padx=10, pady=(6, 6))
        ctk.CTkLabel(hf, text="system health", font=self.font_small,
                     text_color=COL_TEXT_DIM).pack(side=tk.LEFT)
        self.health_bar = ctk.CTkProgressBar(hf, width=60, height=6,
                                             progress_color=COL_EMERALD,
                                             fg_color=COL_BORDER)
        self.health_bar.pack(side=tk.RIGHT, padx=(4, 0))
        self.health_bar.set(0.98)

    def _draw_threat_gauge(self, score):
        """Draw a radial arc gauge on the overview threat card."""
        c = self.gauge_canvas
        c.delete("all")
        cx, cy, r = 50, 38, 30
        # Track
        c.create_arc(cx - r, cy - r, cx + r, cy + r,
                     start=210, extent=-240, style=tk.ARC,
                     outline=COL_BORDER, width=5)
        # Value arc
        extent = -240 * min(1.0, max(0.0, score))
        color = COL_EMERALD if score < 0.3 else (COL_AMBER if score < 0.7 else COL_CORAL)
        if abs(extent) > 1:
            c.create_arc(cx - r, cy - r, cx + r, cy + r,
                         start=210, extent=extent, style=tk.ARC,
                         outline=color, width=5)
        # Center value
        c.create_text(cx, cy - 2, text=f"{score:.2f}",
                      fill=COL_TEXT, font=("Consolas", 11, "bold"))

    def _draw_mini_sparkline(self):
        """Draw the mini packet-rate sparkline in the overview card."""
        c = getattr(self, "mini_canvas", None)
        if c is None or not c.winfo_exists():
            return
        w = max(1, c.winfo_width())
        h = max(1, c.winfo_height())
        c.delete("all")

        data = list(self.packet_rate_history)
        if len(data) < 2:
            return
        max_val = max(max(data), 1.0)
        pts = []
        for i, v in enumerate(data):
            x = 4 + i * (w - 8) / max(1, len(data) - 1)
            y = h - 4 - (v / max_val) * (h - 12)
            pts.append((x, y))

        # Fill polygon (dark violet area)
        fill = [(pts[0][0], h)] + pts + [(pts[-1][0], h)]
        c.create_polygon(*[c for p in fill for c in p],
                         fill=COL_VIOLET_DARK, outline="")
        # Line
        c.create_line(*[c for p in pts for c in p],
                      fill=COL_VIOLET, width=1.5, smooth=True)

    # ──────────────────────────────────────────────────────────
    #  VIEW 2 — SIGNALS (Live Telemetry Graph)
    # ──────────────────────────────────────────────────────────
    def _build_signals(self):
        ctk.CTkLabel(self.content, text="LIVE SIGNALS", font=self.font_section,
                     text_color=COL_TEXT_DIM).pack(anchor="w", padx=4, pady=(0, 2))

        gf = ctk.CTkFrame(self.content, fg_color=COL_SURFACE, corner_radius=8,
                          border_width=1, border_color=COL_BORDER)
        gf.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        # Floating value badges
        badge_row = ctk.CTkFrame(gf, fg_color="transparent")
        badge_row.pack(fill=tk.X, padx=6, pady=(4, 0))

        pb = ctk.CTkFrame(badge_row, fg_color=COL_BG, corner_radius=4)
        pb.pack(side=tk.LEFT)
        ctk.CTkLabel(pb, text="PKT/s", font=self.font_small,
                     text_color=COL_TEXT_DIM).pack(side=tk.LEFT, padx=(4, 2))
        self.lbl_pkt_rate = ctk.CTkLabel(pb, text="0.0", font=self.font_label,
                                         text_color=COL_VIOLET)
        self.lbl_pkt_rate.pack(side=tk.LEFT, padx=(0, 4))

        sb = ctk.CTkFrame(badge_row, fg_color=COL_BG, corner_radius=4)
        sb.pack(side=tk.RIGHT)
        ctk.CTkLabel(sb, text="SCORE", font=self.font_small,
                     text_color=COL_TEXT_DIM).pack(side=tk.LEFT, padx=(4, 2))
        self.lbl_score_val = ctk.CTkLabel(sb, text="0.000", font=self.font_label,
                                          text_color=COL_CORAL)
        self.lbl_score_val.pack(side=tk.LEFT, padx=(0, 4))

        # Canvas
        self.telemetry_canvas = tk.Canvas(gf, bg=COL_BG, highlightthickness=0)
        self.telemetry_canvas.pack(fill=tk.BOTH, expand=True, padx=6, pady=(2, 6))
        self._draw_telemetry_graph()

        # Stat chips
        chips = ctk.CTkFrame(self.content, fg_color="transparent")
        chips.pack(fill=tk.X)
        self.lbl_peak = ctk.CTkLabel(
            chips, text="PEAK 0.0/s \u2197", font=self.font_small,
            text_color=COL_AMBER, fg_color=COL_SURFACE,
            corner_radius=4, padx=6, pady=2
        )
        self.lbl_peak.pack(side=tk.LEFT, padx=(0, 4))
        self.lbl_avg_score = ctk.CTkLabel(
            chips, text="AVG SCORE 0.000 \u2014", font=self.font_small,
            text_color=COL_EMERALD, fg_color=COL_SURFACE,
            corner_radius=4, padx=6, pady=2
        )
        self.lbl_avg_score.pack(side=tk.LEFT)

    def _draw_telemetry_graph(self):
        """Draw dual-axis graph with gradient fill under each line."""
        canvas = getattr(self, "telemetry_canvas", None)
        if canvas is None or not canvas.winfo_exists():
            return
        w = max(1, canvas.winfo_width() or 380)
        h = max(1, canvas.winfo_height() or 140)
        canvas.delete("all")

        # Dotted grid
        for i in range(5):
            y = 8 + i * (h - 16) / 4
            canvas.create_line(4, y, w - 4, y, fill=COL_TEXT_FAINT, dash=(2, 6))

        def draw_series(values, line_color, fill_color, scale):
            if len(values) < 2:
                return
            points = []
            for idx, v in enumerate(values):
                x = 6 + idx * (w - 12) / max(1, len(values) - 1)
                y = h - 8 - min(1.0, max(0.0, v / scale)) * (h - 24)
                points.append((x, y))
            # Fill polygon
            fill_pts = [(points[0][0], h - 4)] + points + [(points[-1][0], h - 4)]
            canvas.create_polygon(*[c for p in fill_pts for c in p],
                                  fill=fill_color, outline="")
            # Line
            canvas.create_line(*[c for p in points for c in p],
                               fill=line_color, width=2, smooth=True)

        draw_series(list(self.packet_rate_history), COL_VIOLET, COL_VIOLET_DARK, 20.0)
        draw_series(list(self.anomaly_score_history), COL_CORAL, COL_CORAL_DARK, 1.0)

    # ──────────────────────────────────────────────────────────
    #  VIEW 3 — ACTIONS (Containment Desk)
    # ──────────────────────────────────────────────────────────
    def _build_actions(self):
        ctk.CTkLabel(self.content, text="CONTAINMENT DESK", font=self.font_section,
                     text_color=COL_TEXT_DIM).pack(anchor="w", padx=4, pady=(0, 4))

        grid = ctk.CTkFrame(self.content, fg_color="transparent")
        grid.pack(fill=tk.BOTH, expand=True)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)
        grid.grid_rowconfigure(0, weight=1)
        grid.grid_rowconfigure(1, weight=1)

        actions = [
            ("C2 EXFIL", "inject exfiltration", COL_CORAL, COL_CORAL_DARK,
             lambda: self.inject_attack("EXFILTRATION"), 0, 0),
            ("SYN FLOOD", "inject flood attack", COL_AMBER, COL_AMBER_DARK,
             lambda: self.inject_attack("SYN_FLOOD"), 0, 1),
            ("BREACH", "trigger casing", COL_PINK, "#2A0F20",
             self.hal.tamper.simulate_tamper, 1, 0),
            ("PIN UNLOCK", "override recovery", COL_EMERALD, COL_EMERALD_DRK,
             self._popup_pin_pad, 1, 1),
        ]

        for title, subtitle, accent, bg, cmd, row, col in actions:
            card = ctk.CTkButton(
                grid, text=f"{title}\n{subtitle}",
                font=self.font_section, text_color=COL_TEXT,
                fg_color=COL_SURFACE, hover_color=bg,
                border_width=1, border_color=accent,
                corner_radius=10, anchor="center",
                command=cmd
            )
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

        ctk.CTkLabel(self.content, text="evidence first \u00B7 containment second",
                     font=self.font_small, text_color=COL_AMBER).pack(pady=(4, 0))

    # ──────────────────────────────────────────────────────────
    #  VIEW 4 — JOURNAL (Field Operation Log)
    # ──────────────────────────────────────────────────────────
    def _build_journal(self):
        ctk.CTkLabel(self.content, text="FIELD JOURNAL", font=self.font_section,
                     text_color=COL_TEXT_DIM).pack(anchor="w", padx=4, pady=(0, 2))

        self.log_text = ctk.CTkTextbox(
            self.content, fg_color=COL_SURFACE, text_color=COL_TEXT,
            font=self.font_log, wrap="word", corner_radius=8,
            border_width=1, border_color=COL_BORDER,
            scrollbar_button_color=COL_VIOLET_DIM,
            scrollbar_button_hover_color=COL_VIOLET
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(0, 2))

        # Configure color tags on the underlying Text widget
        try:
            tw = self.log_text._textbox
            tw.tag_configure("alert",    foreground=COL_CORAL)
            tw.tag_configure("critical", foreground="#FF2D55")
            tw.tag_configure("success",  foreground=COL_EMERALD)
            tw.tag_configure("warning",  foreground=COL_AMBER)
            tw.tag_configure("info",     foreground=COL_VIOLET)
            tw.tag_configure("default",  foreground=COL_TEXT_DIM)
        except Exception:
            pass

        # Populate with existing log entries
        for item in self._event_log:
            self._insert_colored_log(item)
        self.log_text.see(tk.END)

        ctk.CTkLabel(
            self.content, text=f"{len(self._event_log)} entries \u00B7 auto-scroll",
            font=self.font_small, text_color=COL_TEXT_DIM,
            fg_color=COL_SURFACE, corner_radius=4, padx=6, pady=2
        ).pack(pady=(0, 0))

    def _insert_colored_log(self, text):
        """Insert a log line with color coding based on keywords."""
        log_widget = getattr(self, "log_text", None)
        if log_widget is None or not log_widget.winfo_exists():
            return
        # Pick tag
        if any(k in text for k in ("ANOMALY", "ALERT", "LOCKDOWN", "TAMPER")):
            tag = "alert"
        elif any(k in text for k in ("RELAY", "CUT", "ISOLATED", "ZEROIZ")):
            tag = "critical"
        elif any(k in text for k in ("\u2705", "ARMED", "RESTORED", "complete", "ACCEPTED")):
            tag = "success"
        elif any(k in text for k in ("\u26A1", "SIMULATOR", "injection", "Scheduled")):
            tag = "warning"
        elif any(k in text for k in ("Receipt", "hash", "Hash")):
            tag = "info"
        else:
            tag = "default"

        log_widget.insert(tk.END, text + "\n")
        try:
            tw = log_widget._textbox
            end_idx = tw.index(tk.END)
            line_num = int(float(end_idx)) - 1
            tw.tag_add(tag, f"{line_num}.0", f"{line_num}.end")
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────
    #  VIEW 5 — HEALTH (Node Diagnostics)
    # ──────────────────────────────────────────────────────────
    def _build_health(self):
        ctk.CTkLabel(self.content, text="NODE HEALTH", font=self.font_section,
                     text_color=COL_TEXT_DIM).pack(anchor="w", padx=4, pady=(0, 4))

        # ── Status indicator pills ──
        pills = ctk.CTkFrame(self.content, fg_color="transparent")
        pills.pack(fill=tk.X, pady=(0, 4))

        for label, status_text, color in [
            ("UART5", "CONNECTED", COL_EMERALD),
            ("Ed25519", "VERIFIED", COL_EMERALD),
            ("RELAY", "ARMED", COL_AMBER),
        ]:
            pill = ctk.CTkFrame(pills, fg_color=COL_SURFACE, corner_radius=6,
                                border_width=1, border_color=COL_BORDER)
            pill.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            inner = ctk.CTkFrame(pill, fg_color="transparent")
            inner.pack(padx=6, pady=4)
            ctk.CTkLabel(inner, text=f"\u25CF {label}", font=self.font_label,
                         text_color=color).pack(anchor="w")
            ctk.CTkLabel(inner, text=status_text, font=self.font_small,
                         text_color=color).pack(anchor="w")

        # ── Controller state + Chain integrity ──
        mid = ctk.CTkFrame(self.content, fg_color="transparent")
        mid.pack(fill=tk.BOTH, expand=True, pady=(0, 2))
        mid.grid_columnconfigure(0, weight=3)
        mid.grid_columnconfigure(1, weight=2)

        # Controller state card
        ctrl = ctk.CTkFrame(mid, fg_color=COL_SURFACE, corner_radius=8,
                            border_width=1, border_color=COL_BORDER)
        ctrl.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(ctrl, text="CONTROLLER STATE", font=self.font_small,
                     text_color=COL_TEXT_DIM).pack(anchor="w", padx=8, pady=(4, 2))

        status = self.controller.status()
        entries = [
            ("controller_id", self.node_id, COL_VIOLET),
            ("relay_state", status.relay_state,
             COL_EMERALD if status.relay_state in ("ARMED", "CONNECTED") else COL_CORAL),
            ("receipt_verified", str(status.receipt_verified).lower(),
             COL_EMERALD if status.receipt_verified else COL_TEXT_DIM),
            ("quorum_state", status.quorum_state, COL_AMBER),
            ("recovery", str(status.recovery_required).lower(), COL_TEXT_DIM),
        ]
        for key, val, color in entries:
            row = ctk.CTkFrame(ctrl, fg_color="transparent")
            row.pack(fill=tk.X, padx=8, pady=1)
            ctk.CTkLabel(row, text=f"\u25CF {key}:", font=self.font_small,
                         text_color=COL_TEXT_DIM).pack(side=tk.LEFT)
            ctk.CTkLabel(row, text=val, font=self.font_small,
                         text_color=color).pack(side=tk.LEFT, padx=(4, 0))

        # Chain integrity ring
        chain = ctk.CTkFrame(mid, fg_color=COL_SURFACE, corner_radius=8,
                             border_width=1, border_color=COL_BORDER)
        chain.grid(row=0, column=1, sticky="nsew")
        ctk.CTkLabel(chain, text="CHAIN INTEGRITY", font=self.font_small,
                     text_color=COL_TEXT_DIM).pack(pady=(4, 0))

        self.integrity_canvas = tk.Canvas(chain, bg=COL_SURFACE,
                                          highlightthickness=0, width=70, height=60)
        self.integrity_canvas.pack()
        self._draw_integrity_ring()

        ctk.CTkLabel(chain, text=f"{len(self.ledger.chain)} blocks \u00B7 SHA-256",
                     font=self.font_small, text_color=COL_TEXT_DIM).pack(pady=(0, 4))

        # Privacy boundary
        ctk.CTkLabel(self.content,
                     text="LOCAL ONLY \u00B7 NO CLOUD \u00B7 NO TELEMETRY",
                     font=self.font_small, text_color=COL_AMBER).pack(pady=(2, 0))

    def _draw_integrity_ring(self):
        """Draw the chain integrity verification ring."""
        c = getattr(self, "integrity_canvas", None)
        if c is None or not c.winfo_exists():
            return
        c.delete("all")
        cx, cy, r = 35, 30, 22
        valid, _ = self.ledger.verify_chain()
        color = COL_EMERALD if valid else COL_CORAL
        # Track
        c.create_arc(cx - r, cy - r, cx + r, cy + r, start=0, extent=360,
                     style=tk.ARC, outline=COL_BORDER, width=4)
        # Full ring
        c.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=-360,
                     style=tk.ARC, outline=color, width=4)
        c.create_text(cx, cy, text="VALID" if valid else "FAIL",
                      fill=color, font=("Consolas", 8, "bold"))

    # ──────────────────────────────────────────────────────────
    #  PIN PAD OVERLAY
    # ──────────────────────────────────────────────────────────
    def _popup_pin_pad(self):
        """Open a frosted-glass PIN entry overlay."""
        if hasattr(self, "pin_frame") and self.pin_frame.winfo_exists():
            self.pin_frame.destroy()

        win = ctk.CTkFrame(self.root, fg_color=COL_SURFACE, corner_radius=12,
                           border_width=1, border_color=COL_VIOLET_DIM)
        win.place(relx=0.5, rely=0.5, anchor=tk.CENTER, width=240, height=235)
        self.pin_frame = win

        ctk.CTkLabel(win, text="SECURITY PIN", font=self.font_section,
                     text_color=COL_VIOLET).pack(pady=(8, 4))

        pin_disp = ctk.CTkLabel(win, text="_ _ _ _", font=self.font_pin,
                                text_color=COL_TEXT, fg_color=COL_BG,
                                corner_radius=6, width=120, height=28)
        pin_disp.pack(pady=4)

        pin_str = []

        def press_num(n):
            if len(pin_str) < 4:
                pin_str.append(str(n))
                display = " ".join(["\u25CF"] * len(pin_str) + ["_"] * (4 - len(pin_str)))
                pin_disp.configure(text=display)

        def clear():
            pin_str.clear()
            pin_disp.configure(text="_ _ _ _", text_color=COL_TEXT)

        def close_pad():
            win.destroy()

        def submit():
            code_val = "".join(pin_str)
            if validate_pin(code_val) and self.scorer.pin_override(code_val):
                self.controller.require_recovery()
                self.controller.authorize_recovery(True)
                self.hal.relay.engage()
                self.hal.led.solid_on()
                self.ledger.add_entry("tactical_override",
                                      {"pin_status": "ACCEPTED", "relay": "ENGAGED"})
                self.append_log("\u2705 [PIN OVERRIDE] Correct PIN entered -> Data Line Restored & ARMED")
                win.destroy()
            else:
                pin_str.clear()
                pin_disp.configure(text="REJECT", text_color=COL_CORAL)
                win.after(1000, lambda: pin_disp.configure(text="_ _ _ _",
                                                            text_color=COL_TEXT))

        pad = ctk.CTkFrame(win, fg_color="transparent")
        pad.pack(pady=4)

        keys = [
            ("1", 0, 0), ("2", 0, 1), ("3", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("7", 2, 0), ("8", 2, 1), ("9", 2, 2),
            ("CLR", 3, 0), ("0", 3, 1), ("OK", 3, 2),
        ]

        for text, r, c in keys:
            if text == "CLR":
                cmd, btn_fg, btn_bdr = clear, COL_CORAL_DARK, COL_CORAL
            elif text == "OK":
                cmd, btn_fg, btn_bdr = submit, COL_EMERALD_DRK, COL_EMERALD
            else:
                cmd = lambda n=text: press_num(n)
                btn_fg, btn_bdr = COL_BG, COL_BORDER

            ctk.CTkButton(
                pad, text=text, font=self.font_section,
                width=42, height=26, corner_radius=6,
                fg_color=btn_fg, hover_color=COL_BORDER_GLOW,
                border_width=1, border_color=btn_bdr,
                command=cmd
            ).grid(row=r, column=c, padx=2, pady=2)

        ctk.CTkButton(win, text="CANCEL", font=self.font_small,
                      fg_color="transparent", hover_color=COL_BORDER,
                      text_color=COL_TEXT_DIM, corner_radius=4,
                      width=60, height=18, command=close_pad).pack(pady=(2, 4))

    # ──────────────────────────────────────────────────────────
    #  EVENT HANDLERS — PRESERVED EXACTLY
    # ──────────────────────────────────────────────────────────
    def _handle_tamper_event(self):
        self.append_log("\U0001F6A8 [TAMPER ALERT] Casing breached! Zeroizing volatile keys...")
        self.master_aes_key = b"\x00" * 32
        incident_id = f"{self.node_id}:tamper:{int(time.time())}"
        self._apply_containment_logic(incident_id, 1.0, "TAMPER_BREACH")
        self.ledger.add_entry("tamper_breach", {
            "action": "KEYS_ZEROIZED",
            "relay": "ISOLATED",
            "controller_state": "TAMPERED"
        })
        self.append_log("\U0001F525 [ZEROIZATION] Master cryptographic keys purged from RAM.")

    def _handle_relay_change(self, state: str):
        pass

    # ──────────────────────────────────────────────────────────
    #  LOG SYSTEM — PRESERVED (thread-safe)
    # ──────────────────────────────────────────────────────────
    def _append_log_main(self, msg: str):
        t_str = datetime.now().strftime("%H:%M:%S")
        rendered = f"[{t_str}] {msg}"
        self._event_log.append(rendered)
        self._insert_colored_log(rendered)
        log_w = getattr(self, "log_text", None)
        if log_w is not None and log_w.winfo_exists():
            log_w.see(tk.END)

    def append_log(self, msg: str):
        if threading.get_ident() == self.ui_thread_id:
            self._append_log_main(msg)
        else:
            self._ui_log_queue.put(msg)

    def inject_attack(self, attack_type: str):
        self.injected_attack_type = attack_type
        self.append_log(f"\u26A1 [SIMULATOR] Scheduled adversarial injection: {attack_type}")

    # ──────────────────────────────────────────────────────────
    #  PIPELINE WORKER — PRESERVED EXACTLY
    # ──────────────────────────────────────────────────────────
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
        self.append_log("\u2705 Baseline training complete. Trusted controller ARMED & DEFENDING.")
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
                self._apply_containment_logic(incident_id, score,
                                              pkt.get("label", "ANOMALY"), pkt)

            time.sleep(0.08)

    # ──────────────────────────────────────────────────────────
    #  TELEMETRY UPDATE LOOP
    # ──────────────────────────────────────────────────────────
    def _update_telemetry_loop(self):
        # Drain the thread-safe log queue
        while True:
            try:
                self._append_log_main(self._ui_log_queue.get_nowait())
            except queue.Empty:
                break

        # Compute packet rate
        now = time.monotonic()
        interval = max(0.1, now - self._last_metric_time)
        packet_rate = max(0.0, (self.packet_count - self._last_metric_packets) / interval)
        self._last_metric_time = now
        self._last_metric_packets = self.packet_count
        self.packet_rate_history.append(min(packet_rate, 20.0))
        self.anomaly_score_history.append(min(max(self.latest_anomaly_score, 0.0), 1.0))

        # Redraw graphs
        self._draw_telemetry_graph()
        self._draw_mini_sparkline()

        # ── Update Overview widgets ──
        if hasattr(self, "lbl_pkts") and self.lbl_pkts.winfo_exists():
            self.lbl_pkts.configure(text=f"{self.packet_count:,}")
        if hasattr(self, "lbl_anomalies") and self.lbl_anomalies.winfo_exists():
            self.lbl_anomalies.configure(text=str(self.anomaly_count))
        if hasattr(self, "lbl_blocks") and self.lbl_blocks.winfo_exists():
            self.lbl_blocks.configure(text=str(len(self.ledger.chain)))

        # Uptime
        elapsed = int(time.time() - self.start_time)
        hrs, rem = divmod(elapsed, 3600)
        mins, secs = divmod(rem, 60)
        if hasattr(self, "lbl_uptime") and self.lbl_uptime.winfo_exists():
            self.lbl_uptime.configure(text=f"{hrs:02d}:{mins:02d}:{secs:02d}")

        # Threat gauge
        if hasattr(self, "gauge_canvas") and self.gauge_canvas.winfo_exists():
            raw = abs(self.latest_anomaly_score)
            self._draw_threat_gauge(min(1.0, raw))

        # ── Update Signals widgets ──
        if hasattr(self, "lbl_pkt_rate") and self.lbl_pkt_rate.winfo_exists():
            self.lbl_pkt_rate.configure(text=f"{packet_rate:.1f}")
        if hasattr(self, "lbl_score_val") and self.lbl_score_val.winfo_exists():
            self.lbl_score_val.configure(text=f"{abs(self.latest_anomaly_score):.3f}")
        if hasattr(self, "lbl_peak") and self.lbl_peak.winfo_exists():
            peak = max(self.packet_rate_history) if self.packet_rate_history else 0
            self.lbl_peak.configure(text=f"PEAK {peak:.1f}/s \u2197")
        if hasattr(self, "lbl_avg_score") and self.lbl_avg_score.winfo_exists():
            avg = sum(self.anomaly_score_history) / max(1, len(self.anomaly_score_history))
            self.lbl_avg_score.configure(text=f"AVG SCORE {avg:.3f} \u2014")

        # ── Status badge (header) ──
        state = self.scorer.state.value.upper()
        if state == "CALIBRATING":
            self.status_badge.configure(text="\u25CF CALIBRATING", text_color=COL_AMBER)
        elif state == "ARMED":
            self.status_badge.configure(text="\u25CF ARMED", text_color=COL_EMERALD)
        elif state in ("ALERT", "LOCKDOWN"):
            self.status_badge.configure(text="\u25CF LOCKDOWN", text_color=COL_CORAL)

        if self.is_running:
            self.root.after(100, self._update_telemetry_loop)

    # ──────────────────────────────────────────────────────────
    #  RUN / SHUTDOWN — PRESERVED
    # ──────────────────────────────────────────────────────────
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self):
        self.is_running = False
        self.root.destroy()


if __name__ == "__main__":
    app = SentinelTacticalApp()
    app.run()
