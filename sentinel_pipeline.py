"""
BlackBox Sentinel — Core Integration Pipeline
Wires all 4 subsystems together:
    M2 (capture) → M3 (score + log) → M1 (relay) → M4 (dashboard update)

This is the Phase 2 integration script — the single most important file
in the project. If this chain works, the project passes.

Author: M2 Systems Engineer (integration owner)
Branch: main (after integration testing)
"""

import os
import sys
import time
import json
import signal
import threading
from datetime import datetime, timezone

# ─── Add module paths ─────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "m1-hardware", "src"))
sys.path.insert(0, os.path.join(ROOT, "m2-systems", "src"))
sys.path.insert(0, os.path.join(ROOT, "m3-ml-ledger", "src"))

from predict import AnomalyScorer, DeviceState
from ledger import HashChainLedger

# Try importing hardware controller (only works on Pi)
try:
    from relay_controller import RelayController, TamperMonitor, StatusLED
    HW_AVAILABLE = True
except Exception:
    HW_AVAILABLE = False

# ─── Configuration ────────────────────────────────────────────
LEDGER_PATH = os.path.join(ROOT, "m3-ml-ledger", "data", "sentinel_ledger.json")
SCORE_LOG_PATH = os.path.join(ROOT, "m3-ml-ledger", "data", "scores.jsonl")
CAPTURE_INTERFACE = "eth0"  # Change per deployment


class SentinelPipeline:
    """
    Main integration pipeline.
    
    Flow:
        1. Boot → Calibration mode (collect baseline)
        2. Baseline collected → Train model → ARM
        3. Armed → Live scoring on each packet
        4. Anomaly → Fire relay → Log event → Alert → LOCKDOWN
        5. PIN override → Re-engage relay → Return to ARMED
    """

    def __init__(self):
        print("=" * 60)
        print("  BlackBox Sentinel — Core Pipeline")
        print("=" * 60)
        
        # ── M3: ML Scorer + Ledger ──
        self.scorer = AnomalyScorer()
        self.ledger = HashChainLedger(LEDGER_PATH)
        
        # ── M1: Hardware (graceful fallback) ──
        if HW_AVAILABLE:
            self.relay = RelayController()
            self.led = StatusLED()
            self.tamper = TamperMonitor(on_tamper_callback=self._handle_tamper)
        else:
            self.relay = None
            self.led = None
            self.tamper = None
            print("[PIPELINE] Running without GPIO — simulation mode")
        
        # State
        self.running = False
        self.packet_count = 0
        self.anomaly_count = 0
        
        # Log boot event
        self.ledger.add_entry("system", {
            "event": "boot",
            "hardware": HW_AVAILABLE,
            "interface": CAPTURE_INTERFACE
        })
        
        print(f"\n[PIPELINE] Ledger: {LEDGER_PATH}")
        print(f"[PIPELINE] Interface: {CAPTURE_INTERFACE}")
        print(f"[PIPELINE] Hardware: {'REAL' if HW_AVAILABLE else 'SIMULATED'}\n")

    def start(self):
        """Start the capture → score → act pipeline."""
        self.running = True
        
        # Set LED to calibration state
        if self.led:
            self.led.off()
        
        # Start calibration
        self.scorer.start_calibration()
        self.ledger.add_entry("calibration", {"event": "started"})
        
        # Begin packet capture loop
        try:
            self._capture_loop()
        except KeyboardInterrupt:
            print("\n[PIPELINE] Shutting down...")
            self.stop()

    def _capture_loop(self):
        """
        Main capture loop using Scapy.
        Each packet is: captured → features extracted → scored → acted upon.
        """
        try:
            from scapy.all import sniff, IP, TCP, UDP
        except ImportError:
            print("[PIPELINE] Scapy not available — running demo mode")
            self._demo_loop()
            return
        
        prev_time = time.time()
        
        def process_packet(pkt):
            nonlocal prev_time
            
            if not self.running:
                return
            
            if IP not in pkt:
                return
            
            # ── M2: Feature extraction ──
            now = time.time()
            features = {
                "packet_size": len(pkt),
                "inter_arrival": now - prev_time,
                "protocol": pkt[IP].proto,
                "src_port": pkt[TCP].sport if TCP in pkt else (pkt[UDP].sport if UDP in pkt else 0),
                "dst_port": pkt[TCP].dport if TCP in pkt else (pkt[UDP].dport if UDP in pkt else 0),
            }
            prev_time = now
            self.packet_count += 1
            
            # ── M3: Score ──
            result = self.scorer.ingest_features(features)
            
            # ── Act on state transitions ──
            self._handle_result(result, features)
        
        print(f"[CAPTURE] Sniffing on {CAPTURE_INTERFACE}...")
        sniff(
            iface=CAPTURE_INTERFACE,
            prn=process_packet,
            store=False,
            stop_filter=lambda _: not self.running
        )

    def _demo_loop(self):
        """Demo loop for testing without Scapy / network interfaces."""
        import numpy as np
        
        print("[DEMO] Generating synthetic traffic...\n")
        prev_time = time.time()
        
        while self.running:
            now = time.time()
            
            # Generate normal traffic
            features = {
                "packet_size": float(np.random.normal(500, 100)),
                "inter_arrival": now - prev_time,
                "protocol": 6,  # TCP
                "src_port": int(np.random.randint(1024, 65535)),
                "dst_port": 80,
            }
            prev_time = now
            self.packet_count += 1
            
            # Inject anomaly every 50 packets (for demo)
            if self.packet_count % 50 == 0 and self.scorer.state == DeviceState.ARMED:
                features = {
                    "packet_size": 15000.0,
                    "inter_arrival": 10.0,
                    "protocol": 17,  # UDP
                    "src_port": 4444,
                    "dst_port": 4444,
                }
                print(f"\n[DEMO] Injecting anomalous packet #{self.packet_count}...")
            
            result = self.scorer.ingest_features(features)
            self._handle_result(result, features)
            
            time.sleep(0.05)  # 20 packets/sec

    def _handle_result(self, result: dict, features: dict):
        """Handle scoring result — trigger appropriate actions."""
        state = result["state"]
        
        # ── Calibration → Armed transition ──
        if state == "armed" and hasattr(self, '_was_calibrating') and self._was_calibrating:
            self._was_calibrating = False
            if self.led:
                self.led.solid_on()
            self.ledger.add_entry("calibration", {"event": "completed", "state": "armed"})
            print(f"\n[PIPELINE] ✅ ARMED — monitoring {self.packet_count} packets/cycle\n")
        
        if state == "calibrating":
            self._was_calibrating = True
            if self.packet_count % 100 == 0:
                remaining = result.get("calibration_remaining", 0)
                print(f"  [CALIBRATE] {result.get('samples_collected', 0)} samples | {remaining:.0f}s remaining")
            return
        
        # ── Anomaly detected ──
        if result.get("is_anomaly", False):
            self.anomaly_count += 1
            score = result.get("score", 0)
            
            print(f"\n[ALERT] ⚡ ANOMALY #{self.anomaly_count} — score: {score:.4f}")
            print(f"  Packet: size={features['packet_size']}, dst_port={features['dst_port']}")
            
            # Log to ledger
            self.ledger.add_entry("anomaly", {
                "features": features,
                "score": score,
                "packet_number": self.packet_count
            }, anomaly_score=score)
            
            # Fire relay
            if self.relay:
                self.relay.isolate()
            if self.led:
                self.led.blink(0.2)
            
            self.scorer.trigger_lockdown()
            
            self.ledger.add_entry("lockdown", {
                "event": "relay_fired",
                "anomaly_count": self.anomaly_count
            })
            
            print("[PIPELINE] 🔒 LOCKDOWN — data line CUT")
            print("[PIPELINE] Awaiting PIN override on touchscreen...\n")
            
            # In production: wait for M4 GUI PIN override
            # For demo: auto-override after 5 seconds
            time.sleep(5)
            self._pin_override("1234")

    def _pin_override(self, pin: str):
        """Handle PIN override from M4 GUI."""
        if self.scorer.pin_override(pin):
            if self.relay:
                self.relay.engage()
            if self.led:
                self.led.solid_on()
            
            self.ledger.add_entry("override", {
                "event": "pin_accepted",
                "state": "armed"
            })
            print("[PIPELINE] ✅ Override accepted — line RESTORED, returning to ARMED\n")

    def _handle_tamper(self):
        """Anti-tamper response — zeroize keys and lock down."""
        print("\n[TAMPER] ⚠️  ENCLOSURE BREACH — ZEROIZING KEYS")
        
        self.ledger.add_entry("tamper", {
            "event": "enclosure_breach",
            "action": "key_zeroization"
        })
        
        # Zeroize keys (wipe sensitive files from tmpfs)
        keys_dir = "/run/sentinel/keys"
        if os.path.exists(keys_dir):
            import shutil
            shutil.rmtree(keys_dir, ignore_errors=True)
            print("[TAMPER] Keys wiped from tmpfs")
        
        if self.relay:
            self.relay.isolate()
        if self.led:
            self.led.blink(0.1)
        
        self.scorer.trigger_lockdown()

    def stop(self):
        """Graceful shutdown."""
        self.running = False
        
        self.ledger.add_entry("system", {
            "event": "shutdown",
            "packets_processed": self.packet_count,
            "anomalies_detected": self.anomaly_count
        })
        
        # Verify ledger integrity
        is_valid, broken_at = self.ledger.verify_chain()
        print(f"\n[LEDGER] Chain integrity: {'VALID ✅' if is_valid else f'BROKEN at #{broken_at} ❌'}")
        print(f"[LEDGER] Total entries: {len(self.ledger.chain)}")
        
        # Cleanup GPIO
        if self.relay:
            self.relay.engage()  # Always restore line on shutdown
            self.relay.cleanup()
        if self.led:
            self.led.off()
            self.led.cleanup()
        if self.tamper:
            self.tamper.cleanup()
        
        print(f"\n[PIPELINE] Shutdown complete.")
        print(f"  Packets processed: {self.packet_count}")
        print(f"  Anomalies detected: {self.anomaly_count}")
        print(f"  Ledger entries: {len(self.ledger.chain)}")


# ─── Entry point ──────────────────────────────────────────────
if __name__ == "__main__":
    pipeline = SentinelPipeline()
    
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: pipeline.stop())
    
    pipeline.start()
