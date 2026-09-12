"""
BlackBox Sentinel — M4 Interactive Tactical GUI & Defense Node Kiosk (Web Edition)
"""
import os
import sys
import time
import json
import threading
import queue
from collections import deque
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = CURRENT_DIR if os.path.isdir(os.path.join(CURRENT_DIR, "m2-systems")) else os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "m3-ml-ledger", "src"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "m2-systems", "sim"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "common"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "m4-gui-venture", "src"))

os.environ["SENTINEL_HARDWARE"] = "sim"

from hal import get_hal
from predict import AnomalyScorer
from ledger import HashChainLedger
from traffic_generator import TrafficGenerator
from pin_security import validate_pin
from trusted_controller_sim import SimTrustedController
from m3_security_contracts import ContainmentReceiptService, Ed25519ReceiptSigner, SoftwareMonotonicCounter, EvidenceSignal, TwoSignalGate
from quorum_state import QuorumState
import base64

app = Flask(__name__)
CORS(app)

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
        
    return jsonify({
        "packets": core.packet_count,
        "anomalies": core.anomaly_count,
        "blocks": len(core.ledger.chain),
        "uptime": f"{hrs:02d}:{mins:02d}:{secs:02d}",
        "state_str": state_str,
        "state_color": state_color,
        "logs": list(core._event_log),
        "rate_history": list(core.packet_rate_history),
        "score_history": list(core.anomaly_score_history)
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

@app.route("/api/pin", methods=["POST"])
def pin():
    code = request.json.get("pin")
    if core.pin_override(code):
        return jsonify({"status": "success"})
    return jsonify({"status": "rejected"}), 403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
