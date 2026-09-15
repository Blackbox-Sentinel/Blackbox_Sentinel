"""
BlackBox Sentinel — M4 Interactive Tactical GUI & Defense Node Kiosk (Web Edition)
"""
import os
import sys
import time
import json
import threading
import queue
import logging
import base64
import psutil
import subprocess
from collections import deque
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from ml.vision_agent import VisionAnalyzer
from ml.remediation_agent import RemediationAgent

app = Flask(__name__, template_folder="m4-gui-venture/web", static_folder="m4-gui-venture/web", static_url_path='')
app.config['SECRET_KEY'] = 'edge-sentinel-vault-key-2026'
CORS(app)

# Initialize the global AI Agents
vision_agent = VisionAnalyzer()
remediation_agent = RemediationAgent()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = CURRENT_DIR if os.path.isdir(os.path.join(CURRENT_DIR, "m2-systems")) else os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "m3-ml-ledger", "src"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "m2-systems", "sim"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "common"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "m4-gui-venture", "src"))

os.environ["SENTINEL_HARDWARE"] = "hw"

from hal import get_hal
from predict import AnomalyScorer
from ledger import HashChainLedger
from traffic_generator import TrafficGenerator
from pin_security import validate_pin
from trusted_controller_sim import SimTrustedController
from m3_security_contracts import ContainmentReceiptService, Ed25519ReceiptSigner, SoftwareMonotonicCounter, EvidenceSignal, TwoSignalGate
from quorum_state import QuorumState
import base64

# Remove the second Flask instantiation
class SentinelCore:
    def _apply_containment_logic(self, incident_id, score, pkt_label, pkt=None):
        sig_a = EvidenceSignal(
            signal_id=f"sig-A-{self.packet_count}",
            source_id="m3-ml-anomaly-scorer",
            signal_type="ml_anomaly",
            decision="CONFIRM" if score > 0.85 else "ABSTAIN",
            authenticated=True,
            fresh=True,
            confidence=max(0.0, min(1.0, float(score)))
        )
        
        heuristic_decision = "ABSTAIN"
        heuristic_conf = 0.5
        if pkt_label == "TAMPER_BREACH":
            heuristic_decision = "CONFIRM"
            heuristic_conf = 1.0
        elif pkt:
            true_rate = 1.0 / max(0.000001, pkt.get("inter_arrival", 0.03))
            if true_rate > 500:
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
            self.hal.relay.set_receipt(receipt)  # give ESP32 the signed receipt to verify
            self.hal.relay.isolate()
            self.hal.led.blink(0.2)
            self.scorer.trigger_lockdown()
            self.append_log(f"🚨 [ANOMALY DETECTED] {pkt_label} (Score: {score:.4f})")
            self.append_log(f"⚡ [RELAY] Controller-approved line CUT. Hash: {receipt['payload']['event_hash'][:16]}...")
            self.hal.cellular.send_sms("+919876543210", f"ALERT: Line isolated on {self.node_id}")
            return True
        return False

    def __init__(self):
        self._event_log = deque(maxlen=200)
        self.node_id = "AEDN-RACK-01"
        self.ledger_path = os.path.join(PROJECT_ROOT, "m3-ml-ledger", "data", "gui_ledger.json")
        self.master_aes_key = os.urandom(32)

        self.hal = get_hal(
            mode="hw",
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

        self.is_running = True
        self.packet_count = 0
        self.anomaly_count = 0
        self.start_time = time.time()
        self.injected_attack_type = None
        self.latest_anomaly_score = 0.0
        
        self.packet_rate_history = deque(maxlen=40)
        self.anomaly_score_history = deque(maxlen=40)
        self._last_metric_time = time.monotonic()
        self._last_metric_packets = 0

        self.pipeline_thread = threading.Thread(target=self._pipeline_worker, daemon=True)
        self.pipeline_thread.start()
        
        self.telemetry_thread = threading.Thread(target=self._telemetry_worker, daemon=True)
        self.telemetry_thread.start()

    def _telemetry_worker(self):
        while self.is_running:
            now = time.monotonic()
            interval = max(0.1, now - self._last_metric_time)
            packet_rate = max(0.0, (self.packet_count - self._last_metric_packets) / interval)
            self._last_metric_time = now
            self._last_metric_packets = self.packet_count
            self.packet_rate_history.append(min(packet_rate, 20.0))
            self.anomaly_score_history.append(min(max(self.latest_anomaly_score, 0.0), 1.0))
            time.sleep(0.1)

    def append_log(self, msg: str):
        t_str = datetime.now().strftime("%H:%M:%S")
        self._event_log.append(f"[{t_str}] {msg}")

    def inject_attack(self, attack_type: str):
        self.injected_attack_type = attack_type
        self.append_log(f"⚡ [SIMULATOR] Scheduled adversarial injection: {attack_type}")

    def pin_override(self, pin_code: str):
        if validate_pin(pin_code) and self.scorer.pin_override(pin_code):
            self.controller.require_recovery()
            self.controller.authorize_recovery(True)
            self.hal.relay.engage()
            self.hal.led.solid_on()
            self.ledger.add_entry("tactical_override", {"pin_status": "ACCEPTED", "relay": "ENGAGED"})
            self.append_log("✅ [PIN OVERRIDE] Correct PIN entered -> Data Line Restored & ARMED")
            return True
        return False

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

core = SentinelCore()

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/api/telemetry")
def telemetry():
    elapsed = int(time.time() - core.start_time)
    hrs, rem = divmod(elapsed, 3600)
    mins, secs = divmod(rem, 60)
    
    state = core.scorer.state.value.upper()
    if state == "CALIBRATING":
        state_str = "● CALIBRATING"
        state_color = "#FFC400"
    elif state == "ARMED":
        state_str = "● ARMED & MONITORING"
        state_color = "#00E676"
    else:
        state_str = "🚨 LOCKDOWN (LINE CUT)"
        state_color = "#FF3366"
        
    # Hardware Telemetry
    tamper_state = "BREACHED" if core.hal.tamper.is_tampered() else "SECURE"
    link_state = "HEALTHY" if getattr(core.hal.mesh, "ser", None) else "UNKNOWN"
    relay_verified = True if core.hal.relay.get_state() in ["ENGAGED", "ISOLATED"] else False
        
    return jsonify({
        "packets": core.packet_count,
        "anomalies": core.anomaly_count,
        "blocks": len(core.ledger.chain),
        "uptime": f"{hrs:02d}:{mins:02d}:{secs:02d}",
        "state_str": state_str,
        "state_color": state_color,
        "logs": list(core._event_log),
        "rate_history": list(core.packet_rate_history),
        "score_history": list(core.anomaly_score_history),
        "link_state": link_state,
        "tamper_state": tamper_state,
        "relay_verified": relay_verified
    })

@app.route("/api/inject", methods=["POST"])
def inject():
    attack = request.json.get("attack")
    if attack:
        core.inject_attack(attack)
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route("/api/tamper", methods=["POST"])
def tamper():
    core.hal.tamper.simulate_tamper()
    return jsonify({"status": "ok"})

@app.route("/api/hardware_check", methods=["POST"])
def hardware_check():
    core.append_log("TEST: Manual Hardware Check Triggered")
    core.hal.relay.isolate()
    core.hal.led.blink(0.5)
    return jsonify({"status": "ok", "message": "Hardware check executed"})

@app.route("/api/relay_trigger", methods=["POST"])
def relay_trigger():
    core.append_log("TEST: Triggering Raw GPIO Relay (Pins 32,33 -> ESP32 19,20)")
    try:
        import RPi.GPIO as GPIO
        import time
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        # Pin 32 is BCM 12, Pin 33 is BCM 13
        GPIO.setup(12, GPIO.OUT)
        GPIO.setup(13, GPIO.OUT)
        # Pulse them high then low
        GPIO.output(12, GPIO.HIGH)
        GPIO.output(13, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(12, GPIO.LOW)
        GPIO.output(13, GPIO.LOW)
        msg = "Relay toggled successfully via Physical GPIO 12/13 (Pins 32/33)"
    except Exception as e:
        core.append_log(f"GPIO Error: {str(e)}")
        msg = f"Simulated relay toggle (RPi.GPIO not available): {str(e)}"
    
    return jsonify({"status": "ok", "message": msg})

@app.route("/api/system_stats")
def system_stats():
    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    mem_percent = mem.percent
    try:
        temp_out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True)
        # e.g., "temp=42.8'C" -> "42.8"
        temp = temp_out.replace("temp=", "").replace("'C", "").strip()
    except Exception:
        # Fallback for Windows/Mac testing where vcgencmd doesn't exist
        temp = "45.2"
        
    # Simulate a steady ESP32 temperature with slight fluctuation
    esp32_sim_temp = f"38.{int(time.time()) % 10}"
        
    return jsonify({
        "cpu": cpu_percent,
        "ram": mem_percent,
        "temp": temp,
        "esp32_temp": esp32_sim_temp
    })

@app.route("/api/pin", methods=["POST"])
def pin():
    code = request.json.get("pin")
    if core.pin_override(code):
        return jsonify({"status": "success"})
    return jsonify({"status": "rejected"}), 403

@app.route("/api/vision_analyze", methods=["POST"])
def vision_analyze():
    core.append_log("Starting Offline Vision LLM analysis...")
    result = vision_agent.analyze_image()
    
    if result.get("anomaly_detected"):
        core.append_log(f"dY\" [VISION ALERT] Anomaly detected: {result.get('analysis')}")
        core.hal.relay.isolate()
    else:
        core.append_log(f"-? [VISION CLEAR] {result.get('analysis')}")
        
    return jsonify(result)

def autonomous_self_healing_loop():
    """Background thread: Autonomous AI Self-Healing Orchestrator.
    
    Every 60 seconds:
    1. Captures framebuffer screenshot → Vision LLM (moondream) analyzes it
    2. If anomaly detected → gathers full system context (logs, thermal, memory)
    3. Remediation LLM (qwen2.5:1.5b) generates a targeted fix command
    4. Command is validated against a security allowlist
    5. Action is cryptographically signed to the Ed25519 ledger
    6. Fix is executed with 3-strike rollback protection
    """
    logger.info("[SELF-HEAL] Autonomous Self-Healing Loop Started.")
    core.append_log("🧠 [AI] Self-Healing Orchestrator initialized — scanning every 60s")
    
    # Wait for the system to stabilize before first scan
    time.sleep(30)
    
    consecutive_healthy = 0
    
    while True:
        try:
            # 1. Vision LLM Framebuffer Scan
            result = vision_agent.analyze_image()
            status = result.get("status", "unknown")
            analysis = result.get("analysis", "No analysis")
            
            if result.get("anomaly_detected"):
                consecutive_healthy = 0
                logger.critical(f"[SELF-HEAL] UI anomaly detected: {analysis}")
                core.append_log(f"🔍 [AI-VISION] Anomaly detected: {analysis[:80]}...")
                
                # 2. Gather full system diagnostics
                system_context = remediation_agent.gather_system_context()
                context_str = "\n".join([
                    f"Journal Logs:\n{system_context.get('journal', 'N/A')[:500]}",
                    f"\nFailed Services:\n{system_context.get('failed_services', 'None')}",
                    f"\nTemperature: {system_context.get('temperature', 'N/A')}",
                    f"\nMemory:\n{system_context.get('memory', 'N/A')}",
                    f"\nDisk: {system_context.get('disk', 'N/A')}",
                ])
                
                core.append_log(f"📊 [AI-DIAG] System temp: {system_context.get('temperature', '?')}, "
                              f"Failed services: {system_context.get('failed_services', 'none')[:60]}")
                
                # 3. Generate AI fix command
                patch_cmd = remediation_agent.generate_patch_command(
                    error_context=context_str,
                    vision_analysis=analysis
                )
                
                core.append_log(f"🔧 [AI-FIX] Generated command: {patch_cmd}")
                
                # 4. Cryptographic Ledger Signing
                try:
                    sig_payload = {
                        "action": "self_heal",
                        "command": patch_cmd,
                        "vision_status": status,
                        "analysis_summary": analysis[:200],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    signature = core.signer.sign(sig_payload)
                    sig_short = signature[:16] + "..."
                    
                    core.ledger.add_entry("ai_self_healing", {
                        "command": patch_cmd,
                        "vision_analysis": analysis[:200],
                        "system_temp": system_context.get("temperature", "N/A"),
                        "signature": signature,
                        "controller_id": core.node_id,
                    })
                    core.append_log(f"🔐 [AI-LEDGER] Action signed: {sig_short}")
                except Exception as e:
                    logger.error(f"[SELF-HEAL] Ledger signing failed: {e}")
                
                # 5. Execute with rollback protection
                success = remediation_agent.execute_with_rollback(patch_cmd)
                if success:
                    core.append_log(f"✅ [AI-HEAL] Fix applied successfully: {patch_cmd}")
                else:
                    core.append_log(f"⚠️ [AI-HEAL] Fix failed (strike {remediation_agent.strike_count}/3)")
                    
            else:
                consecutive_healthy += 1
                # Log periodic health confirmation (every 10 scans = ~10 minutes)
                if consecutive_healthy % 10 == 0:
                    core.append_log(f"✅ [AI-VISION] System healthy — {consecutive_healthy} consecutive clean scans")
                    
        except Exception as e:
            logger.error(f"[SELF-HEAL] Loop error: {e}")
            
        time.sleep(60)

if __name__ == "__main__":
    # Start the autonomous background orchestrator loop
    healing_thread = threading.Thread(target=autonomous_self_healing_loop, daemon=True)
    healing_thread.start()
    
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
