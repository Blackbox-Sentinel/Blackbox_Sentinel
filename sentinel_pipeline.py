"""
BlackBox Sentinel — Master Core Integration Pipeline
Wires all 4 subsystems together via Unified Hardware Abstraction Layer (HAL):
    M2 (inline capture/bridge) -> M3 (ML score + forensic ledger) ->
    M1 (physical relay + LED + cellular + tamper) -> M4 (dashboard)

Author: M2 Systems Engineer
Branch: main
"""

import os
import sys
import time
import json
import signal
import shutil
import threading
from datetime import datetime, timezone

# Ensure stdout handles UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ─── Add module paths ─────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "m1-hardware", "src"))
sys.path.insert(0, os.path.join(ROOT, "m2-systems", "src"))
sys.path.insert(0, os.path.join(ROOT, "m3-ml-ledger", "src"))
sys.path.insert(0, os.path.join(ROOT, "common"))

from hal import get_hal
from predict import AnomalyScorer, DeviceState
from ledger import HashChainLedger

# ─── Configuration ────────────────────────────────────────────
LEDGER_PATH = os.path.join(ROOT, "m3-ml-ledger", "data", "sentinel_ledger.json")
SCORE_LOG_PATH = os.path.join(ROOT, "m3-ml-ledger", "data", "scores.jsonl")
KEYS_DIR = os.getenv("SENTINEL_KEYS_DIR", "/run/sentinel/keys")
CAPTURE_INTERFACE = os.getenv("SENTINEL_INTERFACE", "br0")
EMERGENCY_SMS = os.getenv("SENTINEL_SMS_TARGET", "+919876543210")
NODE_ID = os.getenv("SENTINEL_NODE_ID", "AEDN-NODE-01")


class SentinelPipeline:
    """
    Master Autonomous Edge Defense Node (AEDN) Pipeline.
    
    Flow:
        1. Boot -> Calibration mode (ingest baseline traffic)
        2. Baseline collected -> Train model -> ARM
        3. Armed -> Live scoring on each packet
        4. Anomaly -> Fire relay -> Log to SHA-256 ledger -> OOB SMS -> Mesh Gossip -> LOCKDOWN
        5. PIN override -> Re-engage relay -> Return to ARMED
        6. Enclosure tamper -> Zeroize volatile RAM keys -> Lock down
    """

    def __init__(self):
        print("=" * 65)
        print(f"  🛡️  BlackBox Sentinel — Autonomous Edge Defense Node ({NODE_ID})")
        print("=" * 65)
        
        # ── HAL: Hardware Abstraction Layer (Auto Real/Sim) ──
        self.hal = get_hal(
            on_tamper_callback=self._handle_tamper,
            on_relay_change=self._handle_relay_change,
            node_id=NODE_ID
        )

        # ── M3: ML Scorer + Forensic Ledger ──
        self.scorer = AnomalyScorer()
        self.ledger = HashChainLedger(LEDGER_PATH)
        
        # State
        self.running = False
        self.packet_count = 0
        self.anomaly_count = 0
        
        # Log boot event
        self.ledger.add_entry("system_boot", {
            "node_id": NODE_ID,
            "hal_mode": self.hal.mode,
            "interface": CAPTURE_INTERFACE,
            "timestamp": time.time()
        })
        
        print(f"[PIPELINE] Node ID:    {NODE_ID}")
        print(f"[PIPELINE] Ledger:     {LEDGER_PATH}")
        print(f"[PIPELINE] Interface:  {CAPTURE_INTERFACE}")
        print(f"[PIPELINE] HAL Mode:   {self.hal.mode.upper()}\n")

    def start(self):
        """Start the capture -> score -> act pipeline."""
        self.running = True
        
        # Set LED to calibration state
        self.hal.led.off()
        
        # Start calibration
        self.scorer.start_calibration()
        self.ledger.add_entry("calibration", {"event": "started", "node_id": NODE_ID})
        
        # Begin packet capture loop
        try:
            self._capture_loop()
        except KeyboardInterrupt:
            print("\n[PIPELINE] Shutting down...")
            self.stop()

    def _capture_loop(self):
        """
        Main capture loop. Sniffs packets off the inline bridge br0.
        Falls back cleanly to demo traffic generator on dev machines.
        """
        try:
            from scapy.all import sniff, IP, TCP, UDP
            scapy_available = True
        except ImportError:
            scapy_available = False

        if scapy_available and os.name != "nt":
            self._sniff_scapy()
        else:
            print("[PIPELINE] Network interface capture not active — launching synthetic traffic loop")
            self._demo_loop()

    def _sniff_scapy(self):
        from scapy.all import sniff, IP, TCP, UDP
        prev_time = time.time()

        def process_packet(pkt):
            nonlocal prev_time
            if not self.running or IP not in pkt:
                return

            now = time.time()
            features = {
                "packet_size": float(len(pkt)),
                "inter_arrival": float(now - prev_time),
                "protocol": int(pkt[IP].proto),
                "src_port": int(pkt[TCP].sport if TCP in pkt else (pkt[UDP].sport if UDP in pkt else 0)),
                "dst_port": int(pkt[TCP].dport if TCP in pkt else (pkt[UDP].dport if UDP in pkt else 0)),
            }
            prev_time = now
            self.packet_count += 1
            
            result = self.scorer.ingest_features(features)
            self._handle_result(result, features)

        print(f"[CAPTURE] Sniffing transparently on inline bridge {CAPTURE_INTERFACE}...")
        sniff(
            iface=CAPTURE_INTERFACE,
            prn=process_packet,
            store=False,
            stop_filter=lambda _: not self.running
        )

    def _demo_loop(self):
        """High-fidelity synthetic traffic loop for local development & demonstration."""
        import numpy as np
        sys.path.insert(0, os.path.join(ROOT, "m2-systems", "sim"))
        from traffic_generator import TrafficGenerator
        
        gen = TrafficGenerator()
        print("[DEMO] Streaming simulated enterprise traffic...\n")

        while self.running:
            # Inject attack every 50 packets when armed
            if self.packet_count > 0 and self.packet_count % 50 == 0 and self.scorer.state == DeviceState.ARMED:
                features = gen.generate_attack_packet("EXFILTRATION")
                print(f"\n[DEMO] ⚡ Injecting anomalous packet #{self.packet_count + 1} ({features['label']})...")
            else:
                features = gen.generate_normal_packet()

            self.packet_count += 1
            result = self.scorer.ingest_features(features)
            self._handle_result(result, features)
            time.sleep(0.04)

    def _handle_result(self, result: dict, features: dict):
        """Handle scoring result — trigger hardware & ledger responses."""
        state = result["state"]
        
        # ── Calibration -> Armed transition ──
        if state == "armed" and hasattr(self, '_was_calibrating') and self._was_calibrating:
            self._was_calibrating = False
            self.hal.led.solid_on()
            self.ledger.add_entry("calibration", {"event": "completed", "state": "armed"})
            print(f"\n[PIPELINE] ✅ NODE ARMED — Active anomaly defense running ({self.packet_count} samples processed)\n")
        
        if state == "calibrating":
            self._was_calibrating = True
            if self.packet_count % 50 == 0:
                remaining = result.get("calibration_remaining", 0)
                print(f"  [CALIBRATE] {result.get('samples_collected', 0)} baseline samples | {remaining:.0f}s window remaining")
            return
        
        # ── Anomaly detected ──
        if result.get("is_anomaly", False):
            self.anomaly_count += 1
            score = result.get("score", 0.0)
            
            print(f"\n🚨 [ALERT] ANOMALY #{self.anomaly_count} DETECTED! Reconstruction Error Score: {score:.4f}")
            print(f"  Packet: size={features['packet_size']:.0f}B, dst_port={features['dst_port']}, protocol={features['protocol']}")
            
            # 1. Fire physical/mock mechanical isolation relay
            self.hal.relay.isolate()
            self.hal.led.blink(0.2)
            self.scorer.trigger_lockdown()

            # 2. Commit SHA-256 block to forensic ledger
            entry = self.ledger.add_entry("anomaly_lockdown", {
                "features": features,
                "score": score,
                "packet_number": self.packet_count,
                "action": "RELAY_ISOLATED"
            }, anomaly_score=score)
            print(f"  📋 [LEDGER] Block #{entry['index']} SHA-256: {entry['hash'][:24]}...")

            # 3. Out-of-band cellular SMS alert (SIM800L)
            self.hal.cellular.send_sms(
                EMERGENCY_SMS,
                f"ALERT: Node {NODE_ID} breach detected! Data line physically isolated. Ledger SHA: {entry['hash'][:10]}"
            )

            # 4. ESP-NOW mesh lateral threat gossip
            self.hal.mesh.broadcast_threat({
                "source_node": NODE_ID,
                "threat_score": score,
                "dst_port": features["dst_port"],
                "protocol": features["protocol"]
            })

            print("[PIPELINE] 🔒 LOCKDOWN ACTIVE — Data line mechanically CUT.")
            print("[PIPELINE] Awaiting on-device touchscreen PIN entry to restore data flow...\n")

    def pin_override(self, pin: str) -> bool:
        """Handle Tactical Touchscreen PIN Override (Patent Claim 1)."""
        if self.scorer.pin_override(pin):
            self.hal.relay.engage()
            self.hal.led.solid_on()
            
            self.ledger.add_entry("tactical_override", {
                "event": "pin_accepted",
                "state": "armed",
                "action": "DATA_LINE_RESTORED"
            })
            print("[PIPELINE] ✅ Tactical PIN Override Accepted — Data line mechanically RESTORED\n")
            return True
        return False

    def _handle_tamper(self):
        """Anti-Tamper Housing Breach Handler (Patent Claim 2)."""
        print("\n" + "!" * 65)
        print("🚨 [TAMPER] PHYSICAL ENCLOSURE BREACH DETECTED!")
        print("🔥 [TAMPER] ZEROIZING VOLATILE RAM CRYPTOGRAPHIC KEY VAULT...")
        print("!" * 65)
        
        # Zeroize keys from volatile storage
        if os.path.exists(KEYS_DIR):
            for fname in os.listdir(KEYS_DIR):
                fpath = os.path.join(KEYS_DIR, fname)
                try:
                    size = os.path.getsize(fpath)
                    with open(fpath, "wb") as f:
                        f.write(b"\x00" * size)
                    os.remove(fpath)
                except Exception:
                    pass
            shutil.rmtree(KEYS_DIR, ignore_errors=True)
            print("[TAMPER] Keys purged and zeroized from RAM.")

        self.hal.relay.isolate()
        self.hal.led.blink(0.05)
        self.scorer.trigger_lockdown()

        self.ledger.add_entry("tamper_breach", {
            "event": "enclosure_breach",
            "action": "RAM_KEY_ZEROIZATION",
            "relay": "ISOLATED"
        })

        self.hal.cellular.send_sms(
            EMERGENCY_SMS,
            f"CRITICAL: Node {NODE_ID} casing breached! Keys zeroized, network line severed."
        )

    def _handle_relay_change(self, state: str):
        pass

    def stop(self):
        """Graceful shutdown."""
        self.running = False
        
        self.ledger.add_entry("system_shutdown", {
            "packets_processed": self.packet_count,
            "anomalies_detected": self.anomaly_count
        })
        
        is_valid, broken_at = self.ledger.verify_chain()
        print(f"\n[LEDGER] Forensic Chain Integrity: {'✅ VALID' if is_valid else f'❌ BROKEN at #{broken_at}'}")
        print(f"[LEDGER] Total Committed Blocks: {len(self.ledger.chain)}")
        
        # Restore relay and cleanup HAL
        self.hal.relay.engage()
        self.hal.cleanup()
        
        print("\n[PIPELINE] Shutdown complete.")


# ─── Entry Point ──────────────────────────────────────────────
if __name__ == "__main__":
    pipeline = SentinelPipeline()
    signal.signal(signal.SIGINT, lambda s, f: pipeline.stop())
    pipeline.start()
