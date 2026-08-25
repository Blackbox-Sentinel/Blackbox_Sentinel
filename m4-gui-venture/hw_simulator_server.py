"""
BlackBox Sentinel — Visual Hardware Simulator Server
Runs the Digital Twin pipeline in a background thread and exposes
real-time hardware state to a web-based interactive schematic UI.

No external dependencies — uses only Python standard library.
"""

import os
import sys
import json
import time
import shutil
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Setup paths ──────────────────────────────────────────────────────────
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "m3-ml-ledger", "src"))
sys.path.insert(0, os.path.join(ROOT, "m2-systems", "sim"))
sys.path.insert(0, os.path.join(ROOT, "common"))

os.environ["SENTINEL_HARDWARE"] = "sim"

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
PORT = 8080

# ── Shared State Object (Thread-Safe) ────────────────────────────────────
state_lock = threading.Lock()
hw_state = {
    "phase": "BOOT",
    "device_state": "IDLE",
    "packets_total": 0,
    "anomalies_total": 0,
    "calibration_progress": 0,
    "calibration_max": 120,
    "relay": {"state": "ENGAGED", "gpio": 17, "fired_at": None},
    "tamper": {"state": "SECURE", "gpio_27": True, "gpio_22": True, "breached_at": None},
    "led": {"state": "OFF", "color": "none"},
    "cellular": {"state": "REGISTERED", "rssi": "28/31", "sms_log": []},
    "mesh": {"state": "LISTENING", "broadcasts": []},
    "keystore": {"state": "MOUNTED", "keys_present": True},
    "controller": {"state": "SAFE", "link": "HEALTHY", "decision": "WAITING", "last_transition": None},
    "signals": {"required": ["known_attack", "adaptive_anomaly"], "received": [], "decision": "WAITING"},
    "quorum": {"required": 0, "received": 0, "decision": "NOT_CONFIGURED"},
    "receipt": {"status": "NOT_AVAILABLE", "receipt_id": None, "counter": None, "hash": None, "external_witness": "NOT_CONFIGURED"},
    "power": {"state": "PRIMARY", "hold_up": "NOT_CONFIGURED"},
    "recovery": {"state": "LOCKED", "last_result": None},
    "score_history": [],
    "current_score": 0.0,
    "latest_packet": None,
    "ledger_blocks": [],
    "event_log": [],
    "bridge": {"state": "UP", "eth0": "UP", "eth1": "UP", "packets_forwarded": 0},
    "simulation_running": False,
    "auto_mode": False,
}


def push_event(msg, level="info"):
    """Add timestamped event to the log."""
    with state_lock:
        hw_state["event_log"].append({
            "time": time.strftime("%H:%M:%S"),
            "msg": msg,
            "level": level
        })
        if len(hw_state["event_log"]) > 80:
            hw_state["event_log"] = hw_state["event_log"][-80:]


# ── Hardware Simulation Engine ───────────────────────────────────────────
class HardwareSimEngine:
    """Drives the Digital Twin — updates hw_state as the pipeline runs."""

    def __init__(self):
        from hal import get_hal
        from predict import AnomalyScorer, DeviceState
        from ledger import HashChainLedger
        from traffic_generator import TrafficGenerator
        from security.trusted_controller import TrustedController, load_or_create_shared_secret

        self.DeviceState = DeviceState

        data_dir = os.path.join(ROOT, "m3-ml-ledger", "data")
        os.makedirs(data_dir, exist_ok=True)

        keys_dir = os.path.join(ROOT, "scratch_keys_vault")
        os.makedirs(keys_dir, exist_ok=True)
        key_file = os.path.join(keys_dir, "master_encryption_key.bin")
        if not os.path.exists(key_file):
            with open(key_file, "wb") as f:
                f.write(os.urandom(32))

        self.keys_dir = keys_dir
        self.hal = get_hal(
            mode="sim",
            on_tamper_callback=self._on_tamper,
            on_relay_change=self._on_relay_change,
            node_id="AEDN-RACK-01"
        )
        self.scorer = AnomalyScorer()
        self.controller = TrustedController(secret=load_or_create_shared_secret(), quorum_required=0, freshness_window_seconds=60)
        self.ledger = HashChainLedger(os.path.join(data_dir, "hw_sim_ledger.json"))
        self.traffic_gen = TrafficGenerator()
        self.running = False

        self.ledger.add_entry("system_boot", {
            "node_id": "AEDN-RACK-01",
            "hal_mode": "SIM",
            "timestamp": time.time()
        })
        self._sync_ledger()
        self._sync_controller()
        push_event("System booted. HAL initialized in SIM mode.", "success")

    def _sync_controller(self):
        """Publish safe controller telemetry for M4 without exposing secrets."""
        snapshot = self.controller.snapshot()
        with state_lock:
            hw_state["controller"] = {
                "state": snapshot["controller_state"],
                "link": "HEALTHY",
                "decision": snapshot["quorum"]["decision"],
                "last_transition": time.strftime("%H:%M:%S"),
            }
            hw_state["signals"] = {
                "required": list(self.controller.required_signals),
                "received": snapshot["signals"],
                "decision": snapshot["quorum"]["decision"],
            }
            hw_state["quorum"] = snapshot["quorum"]
            if snapshot["receipt"]:
                receipt = snapshot["receipt"]
                hw_state["receipt"] = {
                    "status": snapshot["receipt_verification"],
                    "receipt_id": receipt["receipt_id"],
                    "counter": receipt["counter"],
                    "hash": receipt["receipt_hash"][:16] + "...",
                    "external_witness": receipt["external_witness_status"],
                }
            hw_state["power"] = {"state": "PRIMARY", "hold_up": "NOT_CONFIGURED"}

    def _sync_ledger(self):
        with state_lock:
            hw_state["ledger_blocks"] = [
                {"index": b["index"], "event_type": b["event_type"],
                 "hash": b["hash"][:16] + "...", "timestamp": b["timestamp"]}
                for b in self.ledger.chain[-20:]
            ]

    def _on_relay_change(self, new_state):
        with state_lock:
            hw_state["relay"]["state"] = new_state
            if new_state == "ISOLATED":
                hw_state["relay"]["fired_at"] = time.strftime("%H:%M:%S")
                hw_state["bridge"]["eth1"] = "CUT"
            else:
                hw_state["relay"]["fired_at"] = None
                hw_state["bridge"]["eth1"] = "UP"

    def _on_tamper(self):
        with state_lock:
            hw_state["tamper"]["state"] = "BREACHED"
            hw_state["tamper"]["gpio_27"] = False
            hw_state["tamper"]["gpio_22"] = False
            hw_state["tamper"]["breached_at"] = time.strftime("%H:%M:%S")
            hw_state["keystore"]["state"] = "ZEROIZED"
            hw_state["keystore"]["keys_present"] = False
        push_event("TAMPER GRID SEVERED! Volatile RAM keys ZEROIZED.", "critical")

        # Zeroize keys
        if os.path.exists(self.keys_dir):
            for fn in os.listdir(self.keys_dir):
                fp = os.path.join(self.keys_dir, fn)
                try:
                    sz = os.path.getsize(fp)
                    with open(fp, "wb") as f:
                        f.write(b"\x00" * sz)
                    os.remove(fp)
                except Exception:
                    pass
            shutil.rmtree(self.keys_dir, ignore_errors=True)

        self.controller.mark_tampered()
        self.hal.relay.isolate()
        self.hal.led.blink(0.05)
        self.scorer.trigger_lockdown()

        entry = self.ledger.add_entry("tamper_zeroization", {
            "action": "KEY_POOL_ZEROIZED",
            "relay": "ISOLATED",
            "trigger": "CHASSIS_BREACH"
        })
        self._sync_ledger()

        self.hal.cellular.send_sms("+919876543210",
            "CRITICAL: AEDN-RACK-01 tamper breach. Keys zeroized.")
        self._sync_controller()
        with state_lock:
            hw_state["cellular"]["sms_log"].append({
                "time": time.strftime("%H:%M:%S"),
                "to": "+919876543210",
                "msg": "CRITICAL: Tamper breach. Keys zeroized."
            })
            hw_state["device_state"] = "LOCKDOWN"
            hw_state["led"]["state"] = "BLINK_FAST"
            hw_state["led"]["color"] = "red"

    def run_calibration(self):
        """Phase 1: Calibrate the Isolation Forest on baseline traffic."""
        with state_lock:
            hw_state["phase"] = "CALIBRATING"
            hw_state["device_state"] = "CALIBRATING"
            hw_state["led"]["state"] = "OFF"
            hw_state["led"]["color"] = "none"
            hw_state["simulation_running"] = True

        self.scorer.start_calibration()
        push_event("Phase 1: Baseline calibration started (120 samples)...", "info")

        for i in range(120):
            if not hw_state["simulation_running"]:
                return
            pkt = self.traffic_gen.generate_normal_packet()
            res = self.scorer.ingest_features(pkt)

            with state_lock:
                hw_state["packets_total"] += 1
                hw_state["calibration_progress"] = i + 1
                hw_state["current_score"] = res.get("score", 0.0)
                hw_state["bridge"]["packets_forwarded"] += 1
                hw_state["latest_packet"] = {
                    "size": int(pkt["packet_size"]),
                    "port": int(pkt["dst_port"]),
                    "proto": int(pkt["protocol"]),
                    "score": round(res.get("score", 0.0), 4)
                }

            if i == 119:
                # Force calibration window to expire
                self.scorer.calibration_start = time.time() - 2000
                self.scorer.ingest_features(pkt)

            time.sleep(0.03)

        with state_lock:
            hw_state["phase"] = "ARMED"
            hw_state["device_state"] = "ARMED"
            hw_state["led"]["state"] = "SOLID"
            hw_state["led"]["color"] = "green"

        self.hal.led.solid_on()
        self.controller.arm()
        self._sync_controller()
        self.ledger.add_entry("state_transition", {"from": "CALIBRATING", "to": "ARMED"})
        self._sync_ledger()
        push_event("Calibration complete. System ARMED & defending.", "success")

    def run_normal_traffic(self, count=30):
        """Phase 2: Monitor normal enterprise traffic."""
        with state_lock:
            hw_state["phase"] = "MONITORING"
        push_event(f"Phase 2: Monitoring {count} normal enterprise packets...", "info")

        for _ in range(count):
            if not hw_state["simulation_running"]:
                return
            if hw_state["device_state"] == "LOCKDOWN":
                return

            pkt = self.traffic_gen.generate_normal_packet()
            res = self.scorer.ingest_features(pkt)
            score = res.get("score", 0.0)

            with state_lock:
                hw_state["packets_total"] += 1
                hw_state["current_score"] = score
                hw_state["bridge"]["packets_forwarded"] += 1
                hw_state["score_history"].append(round(score, 4))
                if len(hw_state["score_history"]) > 60:
                    hw_state["score_history"] = hw_state["score_history"][-60:]
                hw_state["latest_packet"] = {
                    "size": int(pkt["packet_size"]),
                    "port": int(pkt["dst_port"]),
                    "proto": int(pkt["protocol"]),
                    "score": round(score, 4)
                }

            time.sleep(0.15)

    def inject_attack(self, attack_type="EXFILTRATION"):
        """Phase 3: Inject adversarial traffic."""
        if hw_state["device_state"] == "LOCKDOWN":
            push_event("Cannot inject — node already in LOCKDOWN.", "warning")
            return

        with state_lock:
            hw_state["phase"] = "ATTACK_INJECTED"

        pkt = self.traffic_gen.generate_attack_packet(attack_type)
        push_event(f"ATTACK INJECTED: {pkt['label']} ({int(pkt['packet_size'])}B on port {int(pkt['dst_port'])})", "critical")

        res = self.scorer.ingest_features(pkt)
        score = res.get("score", 0.0)
        event_id = f"evt-{int(time.time() * 1000)}"
        signal_a = self.controller.issue_signal(
            event_id=event_id,
            source="m3-known-detector",
            signal_type="known_attack",
            payload={"label": pkt.get("label", attack_type), "score": score},
        )
        signal_b = self.controller.issue_signal(
            event_id=event_id,
            source="m3-adaptive-profile",
            signal_type="adaptive_anomaly",
            payload={"port": int(pkt["dst_port"]), "score": score},
        )
        self.controller.submit_signal(signal_a)
        decision = self.controller.submit_signal(signal_b)

        with state_lock:
            hw_state["packets_total"] += 1
            hw_state["anomalies_total"] += 1
            hw_state["current_score"] = score
            hw_state["score_history"].append(round(score, 4))
            hw_state["latest_packet"] = {
                "size": int(pkt["packet_size"]),
                "port": int(pkt["dst_port"]),
                "proto": int(pkt["protocol"]),
                "score": round(score, 4),
                "label": pkt.get("label", "UNKNOWN")
            }

        if res.get("is_anomaly", False) and decision.get("decision") == "ISOLATE":
            # 1. Fire relay only after both independent signals are accepted.
            self.hal.relay.isolate()
            self.hal.led.blink(0.2)
            self.scorer.trigger_lockdown()
            with state_lock:
                hw_state["device_state"] = "LOCKDOWN"
                hw_state["led"]["state"] = "BLINK"
                hw_state["led"]["color"] = "red"

            push_event(f"ANOMALY DETECTED (score: {score:.4f}). Relay FIRED — line CUT.", "critical")

            # 2. Ledger
            entry = self.ledger.add_entry("anomaly_lockdown", {
                "threat": pkt.get("label", attack_type),
                "score": score,
                "relay": "ISOLATED"
            }, anomaly_score=score)
            self._sync_ledger()
            self._sync_controller()
            push_event(f"SHA-256 Block #{entry['index']} committed: {entry['hash'][:16]}...", "info")

            # 3. SMS
            self.hal.cellular.send_sms("+919876543210",
                f"ALERT: {pkt.get('label', attack_type)} detected. Line isolated.")
            with state_lock:
                hw_state["cellular"]["sms_log"].append({
                    "time": time.strftime("%H:%M:%S"),
                    "to": "+919876543210",
                    "msg": f"ALERT: {pkt.get('label', attack_type)}"
                })
            push_event("OOB SMS dispatched via SIM800L to admin.", "info")

            # 4. Mesh
            self.hal.mesh.broadcast_threat({"threat": pkt.get("label", attack_type), "score": score})
            with state_lock:
                hw_state["mesh"]["broadcasts"].append({
                    "time": time.strftime("%H:%M:%S"),
                    "threat": pkt.get("label", attack_type)
                })
            push_event("ESP-NOW mesh gossip broadcast to peer nodes.", "info")
        elif res.get("is_anomaly", False):
            self._sync_controller()
            push_event("Anomaly held pending: trusted controller requires both independent signals.", "warning")

    def pin_override(self, pin="1234"):
        """Phase 4: Tactical touchscreen PIN override."""
        if self.scorer.pin_override(pin):
            self.controller.recover()
            self.hal.relay.engage()
            self.hal.led.solid_on()
            with state_lock:
                hw_state["device_state"] = "ARMED"
                hw_state["phase"] = "ARMED"
                hw_state["led"]["state"] = "SOLID"
                hw_state["led"]["color"] = "green"
                hw_state["relay"]["fired_at"] = None
                hw_state["bridge"]["eth1"] = "UP"

            self.ledger.add_entry("tactical_override", {"pin": "ACCEPTED", "relay": "RESTORED"})
            self._sync_ledger()
            self._sync_controller()
            with state_lock:
                hw_state["recovery"] = {"state": "RECOVERED", "last_result": "ACCEPTED"}
            push_event("PIN override accepted. Relay RESTORED. System ARMED.", "success")
            return True
        else:
            with state_lock:
                hw_state["recovery"] = {"state": "LOCKED", "last_result": "REJECTED"}
            push_event("PIN REJECTED. Line remains CUT.", "warning")
            return False

    def trigger_tamper(self):
        """Phase 5: Simulate chassis breach."""
        push_event("Physical tamper switch tripped — casing breach!", "critical")
        self.hal.tamper.simulate_tamper()

    def audit_chain(self):
        """Phase 6: Verify forensic ledger integrity."""
        is_valid, broken_at = self.ledger.verify_chain()
        if is_valid:
            push_event(f"Forensic audit PASSED: {len(self.ledger.chain)} blocks, 100% valid.", "success")
        else:
            push_event(f"Forensic audit FAILED at block #{broken_at}!", "critical")
        return is_valid

    def run_auto_demo(self):
        """Runs the full 6-phase Digital Twin cycle automatically."""
        with state_lock:
            hw_state["auto_mode"] = True

        self.run_calibration()
        time.sleep(0.5)
        self.run_normal_traffic(20)
        time.sleep(0.5)
        self.inject_attack("EXFILTRATION")
        time.sleep(2)
        self.pin_override("1234")
        time.sleep(1)
        self.run_normal_traffic(10)
        time.sleep(0.5)
        self.trigger_tamper()
        time.sleep(1)
        self.audit_chain()

        with state_lock:
            hw_state["auto_mode"] = False
            hw_state["simulation_running"] = False
        push_event("Full Digital Twin validation cycle COMPLETE.", "success")


# ── Initialize Engine ────────────────────────────────────────────────────
engine = None
engine_lock = threading.Lock()


def get_engine():
    global engine
    with engine_lock:
        if engine is None:
            engine = HardwareSimEngine()
    return engine


# ── HTTP Request Handler ─────────────────────────────────────────────────
class SimulatorHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        pass  # Quiet logging

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/state":
            with state_lock:
                data = json.dumps(hw_state)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data.encode("utf-8"))
            return

        if parsed.path == "/api/action":
            params = parse_qs(parsed.query)
            action = params.get("do", [""])[0]
            eng = get_engine()

            def run_in_thread(fn, *a):
                t = threading.Thread(target=fn, args=a, daemon=True)
                t.start()

            if action == "auto_demo":
                run_in_thread(eng.run_auto_demo)
                resp = {"ok": True, "action": "auto_demo_started"}
            elif action == "calibrate":
                run_in_thread(eng.run_calibration)
                resp = {"ok": True, "action": "calibration_started"}
            elif action == "monitor":
                run_in_thread(eng.run_normal_traffic, 30)
                resp = {"ok": True, "action": "monitoring_started"}
            elif action == "attack":
                atk_type = params.get("type", ["EXFILTRATION"])[0]
                run_in_thread(eng.inject_attack, atk_type)
                resp = {"ok": True, "action": f"attack_{atk_type}"}
            elif action == "pin_override":
                pin = params.get("pin", ["1234"])[0]
                run_in_thread(eng.pin_override, pin)
                resp = {"ok": True, "action": "pin_override"}
            elif action == "tamper":
                run_in_thread(eng.trigger_tamper)
                resp = {"ok": True, "action": "tamper_triggered"}
            elif action == "audit":
                run_in_thread(eng.audit_chain)
                resp = {"ok": True, "action": "audit_started"}
            elif action == "stop":
                with state_lock:
                    hw_state["simulation_running"] = False
                resp = {"ok": True, "action": "stopped"}
            else:
                resp = {"ok": False, "error": f"Unknown action: {action}"}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        # Default: serve static files (simulator.html, etc.)
        if parsed.path == "/" or parsed.path == "":
            self.path = "/simulator.html"
        super().do_GET()


# ── Main ─────────────────────────────────────────────────────────────────
def main():
    # Pre-initialize the engine
    get_engine()

    server = HTTPServer(("0.0.0.0", PORT), SimulatorHandler)
    url = f"http://localhost:{PORT}"
    print("=" * 65)
    print("  BLACKBOX SENTINEL — VISUAL HARDWARE SIMULATOR")
    print(f"  URL: {url}")
    print(f"  Web Dir: {WEB_DIR}")
    print("=" * 65)
    print("  Open the URL in your browser to see the interactive schematic.")
    print("  Click 'Run Full Demo' to watch the complete AEDN lifecycle.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down simulator server.")
        server.server_close()


if __name__ == "__main__":
    main()
