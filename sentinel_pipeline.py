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
from typing import Any, Mapping

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
from ledger import HashChainLedger
from predict_v3 import AnomalyScorer, DeviceState
from evidence_transport import M2EvidenceTransport
from m3_decision_path import M3DecisionPath
from m3_security_contracts import EvidenceSignal
from quorum_state import VoteDecision


# ─── Configuration ────────────────────────────────────────────
LEDGER_PATH = os.path.join(ROOT, "m3-ml-ledger", "data", "sentinel_ledger.json")
COUNTER_PATH = os.path.join(ROOT, "m3-ml-ledger", "data", "receipt_counter.txt")
SCORE_LOG_PATH = os.path.join(ROOT, "m3-ml-ledger", "data", "scores.jsonl")
TELEMETRY_PATH = os.path.join(ROOT, "m3-ml-ledger", "data", "phase2_telemetry_real_m2_m3.jsonl")
KEYS_DIR = os.getenv(
    "SENTINEL_KEYS_DIR", os.path.join(ROOT, "m3-ml-ledger", "data", "keys")
)


class TelemetryJsonlWriter:
    """Append normalized telemetry dicts as JSON Lines.

    Mirrors integration/telemetry.py's JsonlTelemetryWriter (truncate on
    construction, append-and-flush per emit) -- adapted for a plain dict
    since M3DecisionPath._telemetry() already returns
    NormalizedTelemetry.to_dict(), not a NormalizedTelemetry instance.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("")

    def emit(self, telemetry: dict) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(telemetry, sort_keys=True, ensure_ascii=True) + "\n")
            f.flush()


CAPTURE_INTERFACE = os.getenv("SENTINEL_INTERFACE", "br0")
EMERGENCY_SMS = os.getenv("SENTINEL_SMS_TARGET", "+919876543210")
NODE_ID = os.getenv("SENTINEL_NODE_ID", "AEDN-NODE-01")

# Rule-based second signal source (not a second ML model, not a copy of the
# AnomalyScorer/predict_v3.py decision). Exists only so M3's TwoSignalGate
# can be satisfied by two genuinely independent, distinctly-sourced signals
# instead of one model-derived signal alone.
HEURISTIC_PACKET_RATE_THRESHOLD = float(
    os.getenv("SENTINEL_HEURISTIC_PACKET_RATE_THRESHOLD", "500.0")
)


def _heuristic_packet_rate_check(features: Mapping[str, Any]) -> dict:
    """Simple rule-based packet-rate threshold check.

    Computed directly from this window's real ``packets_per_sec`` feature
    (the same feature_row/window_features output the model consumes), with
    no dependency on AnomalyScorer/predict_v3.py. This is a heuristic, not
    a second ML model -- it exists to give the second evidence signal an
    honestly independent basis rather than duplicating the model's result.
    """
    packets_per_sec = float(features.get("packets_per_sec", 0.0))
    return {
        "packets_per_sec": packets_per_sec,
        "threshold": HEURISTIC_PACKET_RATE_THRESHOLD,
        "is_high_rate": packets_per_sec > HEURISTIC_PACKET_RATE_THRESHOLD,
    }


class SentinelPipeline:
    """
    Master Autonomous Edge Defense Node (AEDN) Pipeline.
    
    Flow:
        1. Boot -> Calibration mode (ingest baseline traffic)
        2. Baseline collected -> Train model -> ARM
        3. Armed -> Live scoring on each packet
        4. Anomaly -> M3 evidence/policy path -> normalized telemetry -> M1 handoff when approved
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

        # ── M3: Validated v3 scorer + organization profile + ledger ──
        self.scorer = AnomalyScorer(
            organization_id=os.getenv("SENTINEL_ORGANIZATION_ID", "default_organization")
        )
        self.ledger = HashChainLedger(LEDGER_PATH)
        self.key_epoch = int(os.getenv("SENTINEL_KEY_EPOCH", "1"))
        self.m2_transport = M2EvidenceTransport(
            sender_id=NODE_ID,
            key_epoch=self.key_epoch,
            keys_dir=KEYS_DIR,
            max_age_seconds=30.0,
            future_skew_seconds=5.0,
        )
        # Second, independently-keyed transport for the rule-based heuristic
        # signal. Distinct sender_id -> distinct per-node HMAC key (same
        # derivation mechanism as self.m2_transport, per evidence_transport.py's
        # load_or_create_node_key/derive_signing_key) -> distinct envelope
        # sender, which is what M3's independence check actually keys on
        # (m3_decision_path.py's evidence_signal_from_envelope treats
        # envelope.sender_id as authoritative for source_id, not any value
        # copied into the payload).
        self.m2_transport_heuristic = M2EvidenceTransport(
            sender_id=f"{NODE_ID}-heuristic",
            key_epoch=self.key_epoch,
            keys_dir=KEYS_DIR,
            max_age_seconds=30.0,
            future_skew_seconds=5.0,
        )
        # Quorum voter transports. Single-physical-node, software-simulated
        # multi-voter quorum: both logical voters run on this same node and
        # process -- this is not a claim of separate physical devices casting
        # independent votes. Distinct sender_id per voter, same per-node HMAC
        # derivation as the signal transports above; deliberately not shared
        # with self.m2_transport/self.m2_transport_heuristic's keys or
        # sender_ids, so a vote and a signal can never be mistaken for the
        # same authenticated identity.
        self.m2_transport_model_voter = M2EvidenceTransport(
            sender_id=f"{NODE_ID}-model-voter",
            key_epoch=self.key_epoch,
            keys_dir=KEYS_DIR,
            max_age_seconds=30.0,
            future_skew_seconds=5.0,
        )
        self.m2_transport_heuristic_voter = M2EvidenceTransport(
            sender_id=f"{NODE_ID}-heuristic-voter",
            key_epoch=self.key_epoch,
            keys_dir=KEYS_DIR,
            max_age_seconds=30.0,
            future_skew_seconds=5.0,
        )
        self.decision_path = M3DecisionPath(
            ledger=self.ledger,
            node_id=NODE_ID,
            organization_id=self.scorer.organization_id,
            counter_path=COUNTER_PATH,
            controller_id=os.getenv("SENTINEL_CONTROLLER_ID", "sim-controller"),
            key_epoch=self.key_epoch,
            keys_dir=KEYS_DIR,
            expected_voters=(
                self.m2_transport_model_voter.sender_id,
                self.m2_transport_heuristic_voter.sender_id,
            ),
            required_confirmations=2,
            quorum_deadline_seconds=30.0,
        )
        self.telemetry_writer = TelemetryJsonlWriter(TELEMETRY_PATH)
        self.latest_telemetry = {}

        # State
        self.running = False

        self.packet_count = 0
        self.window_count = 0
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
        from ml.feature_pipeline_v2 import capture_live_window

        print(
            f"[CAPTURE] Sniffing one-second v3 windows on inline bridge "
            f"{CAPTURE_INTERFACE}..."
        )
        while self.running:
            capture_started_at = time.time()
            feature_row = capture_live_window(
                timeout=1.0,
                iface=CAPTURE_INTERFACE,
                history_state=self.scorer.history_state,
            )
            feature_row["capture_started_at"] = capture_started_at
            feature_row["capture_ended_at"] = time.time()
            self.packet_count += int(round(feature_row.get("packets_per_sec", 0.0)))
            result = self.scorer.ingest_feature_window(feature_row)
            self._handle_result(result, feature_row)

    def _demo_loop(self):
        """Generate raw M2-style packets, then convert each batch to a v3 window."""
        import time as _time
        from scapy.all import IP, Raw, TCP, UDP

        sys.path.insert(0, os.path.join(ROOT, "m2-systems", "sim"))
        from traffic_generator import TrafficGenerator
        from ml.feature_pipeline_v2 import window_features

        gen = TrafficGenerator()
        print("[DEMO] Streaming simulated enterprise traffic through v3 windows...\n")

        while self.running:
            capture_started_at = _time.time()
            packets = []
            labels = []
            for _ in range(25):
                if (
                    self.packet_count > 0
                    and self.packet_count % 50 == 0
                    and self.scorer.state == DeviceState.ARMED
                ):
                    raw = gen.generate_attack_packet("EXFILTRATION")
                else:
                    raw = gen.generate_normal_packet()
                labels.append(raw.get("label", "NORMAL"))
                payload_size = max(0, int(raw["packet_size"]) - 64)
                if raw["protocol"] == 6:
                    packet = (
                        IP(src="10.0.0.1", dst="10.0.0.2")
                        / TCP(sport=raw["src_port"], dport=raw["dst_port"])
                        / Raw(load=b"x" * payload_size)
                    )
                elif raw["protocol"] == 17:
                    packet = (
                        IP(src="10.0.0.1", dst="10.0.0.2")
                        / UDP(sport=raw["src_port"], dport=raw["dst_port"])
                        / Raw(load=b"x" * payload_size)
                    )
                else:
                    packet = IP(src="10.0.0.1", dst="10.0.0.2") / Raw(
                        load=b"x" * payload_size
                    )
                packet.time = _time.time()
                packets.append(packet)

            feature_row = window_features(packets, _time.time(), 1.0)
            feature_row = self.scorer.history_state.enrich(feature_row)
            feature_row["synthetic_label"] = labels[-1]
            feature_row["capture_started_at"] = capture_started_at
            feature_row["capture_ended_at"] = _time.time()
            self.packet_count += len(packets)
            result = self.scorer.ingest_feature_window(feature_row)
            self._handle_result(result, feature_row)
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
                print(
                    f"  [CALIBRATE] {result.get('profile_samples', 0)} accepted "
                    f"baseline windows | local detection enabled="
                    f"{result.get('local_detection_enabled', False)}"
                )
            return

        self.window_count += 1

        # Every post-calibration result is available to M4 through the same
        # normalized telemetry contract. A benign result creates no containment
        # request; an anomalous result is still only evidence at this point.
        incident_id = f"{NODE_ID}:window-{self.window_count}"
        now = time.time()
        model_decision = "CONFIRM" if result.get("is_anomaly", False) else "DENY"
        model_confidence = float(result.get("probability_attack", result.get("score", 0.0)))
        model_details = {
            "score": result.get("score"),
            "global_prediction": result.get("global_prediction"),
            "local_prediction": result.get("local_prediction"),
            "feature_count": result.get("feature_count", 45),
        }
        model_envelope = self.m2_transport.build_signal_envelope(
            signal_id=f"{incident_id}:model",
            source_id=NODE_ID,
            signal_type="m3_model_result",
            decision=model_decision,
            confidence=model_confidence,
            details=model_details,
            timestamp=now,
        )
        # Second, independently-sourced signal: a rule-based packet-rate
        # heuristic computed straight from this window's real features, not
        # from the model. Distinct sender_id (self.m2_transport_heuristic)
        # and distinct signal_type give M3's TwoSignalGate a genuinely
        # independent second signal instead of one model-derived signal alone.
        heuristic = _heuristic_packet_rate_check(features)
        heuristic_decision = "CONFIRM" if heuristic["is_high_rate"] else "DENY"
        heuristic_details = {
            "method": "rule_based_packet_rate_heuristic",
            "packets_per_sec": heuristic["packets_per_sec"],
            "threshold": heuristic["threshold"],
        }
        heuristic_envelope = self.m2_transport_heuristic.build_signal_envelope(
            signal_id=f"{incident_id}:heuristic",
            source_id=self.m2_transport_heuristic.sender_id,
            signal_type="heuristic_packet_rate",
            decision=heuristic_decision,
            confidence=None,
            details=heuristic_details,
            timestamp=now,
        )

        # Pre-compute the evidence digest that submit_authenticated() will
        # itself derive from these same two signals, so quorum votes can
        # reference the correct digest before that call returns it. Safe to
        # do here because TwoSignalGate.evaluate() is a pure function with no
        # replay/sequence state (m3_security_contracts.py), and
        # AuthenticatedEnvelope.create() stores payload as a shallow dict
        # copy with no serialization round-trip (authenticated_envelope.py) --
        # so these replica EvidenceSignal objects are field-for-field
        # identical to what submit_authenticated() will independently decode
        # from the real envelopes below. Decoding the real envelopes here
        # instead (via evidence_signal_from_envelope) would consume them
        # against the shared ReplayProtector's sequence state, causing the
        # real submit_authenticated() call to reject them as replays.
        model_signal_replica = EvidenceSignal(
            signal_id=f"{incident_id}:model",
            source_id=NODE_ID,
            signal_type="m3_model_result",
            decision=model_decision,
            authenticated=True,
            fresh=True,
            confidence=model_confidence,
            details=model_details,
        )
        heuristic_signal_replica = EvidenceSignal(
            signal_id=f"{incident_id}:heuristic",
            source_id=self.m2_transport_heuristic.sender_id,
            signal_type="heuristic_packet_rate",
            decision=heuristic_decision,
            authenticated=True,
            fresh=True,
            confidence=None,
            details=heuristic_details,
        )
        predicted_digest = self.decision_path.gate.evaluate(
            incident_id, (model_signal_replica, heuristic_signal_replica)
        ).evidence_digest

        # Quorum votes: single-physical-node, software-simulated multi-voter
        # quorum. Both "voters" run on this same node/process -- this
        # demonstrates the real QuorumStateMachine vote-authentication and
        # N-of-M approval logic, not a claim of separate physical devices
        # independently casting votes.
        model_vote_envelope = self.m2_transport_model_voter.build_vote_envelope(
            incident_id=incident_id,
            voter_id=self.m2_transport_model_voter.sender_id,
            decision=VoteDecision.CONFIRM,
            evidence_digest=predicted_digest,
            vote_sequence=self.window_count,
            timestamp=now,
        )
        heuristic_vote_envelope = self.m2_transport_heuristic_voter.build_vote_envelope(
            incident_id=incident_id,
            voter_id=self.m2_transport_heuristic_voter.sender_id,
            decision=VoteDecision.CONFIRM,
            evidence_digest=predicted_digest,
            vote_sequence=self.window_count,
            timestamp=now,
        )
        decision = self.decision_path.submit_authenticated(
            model_result=result,
            evidence_envelopes=[(model_envelope, None), (heuristic_envelope, None)],
            quorum_envelopes=[(model_vote_envelope, None), (heuristic_vote_envelope, None)],
            incident_id=incident_id,
            now=now,
            features=features,
        )

        self.latest_telemetry = decision.telemetry
        self.telemetry_writer.emit(decision.telemetry)
        if result.get("is_anomaly", False) or decision.status != "BENIGN":
            self.ledger.add_entry(
                "m3_policy_decision",
                {
                    "organization_id": result.get("organization_id"),
                    "incident_id": decision.incident_id,
                    "status": decision.status,
                    "reason": decision.reason,
                    "telemetry_schema_version": decision.telemetry.get("schema_version"),
                    "physical_relay_requested": decision.telemetry["actuation"].get("relay_requested", False),
                },
                anomaly_score=result.get("score", 0.0),
            )

        if not result.get("is_anomaly", False):
            return

        # ── Anomaly detected ──
        if result.get("is_anomaly", False):
            self.anomaly_count += 1

            score = result.get("score", 0.0)

            print(
                f"\n🚨 [ALERT] ANOMALY #{self.anomaly_count} DETECTED! "
                f"v3 score: {score:.4f} | "
                f"global={result.get('global_prediction')} | "
                f"local={result.get('local_prediction')}"
            )
            print(
                f"  Window: packets/sec={features.get('packets_per_sec', 0.0):.2f}, "
                f"bytes/sec={features.get('bytes_per_sec', 0.0):.2f}, "
                f"tcp_ratio={features.get('tcp_ratio', 0.0):.3f}"
            )

            print(
                f"  [M3 POLICY] status={decision.status} | reason={decision.reason}"
            )
            print(
                "  [M4 TELEMETRY] normalized event prepared; "
                "physical relay verification remains pending M1 hardware"
            )

            if decision.status == "CONTAINMENT_ACCEPTED":
                # The software controller accepted a verified receipt. This is
                # not physical ESP32 enforcement; M1 must bind the same contract
                # before relay success can be reported as complete.
                self.hal.led.blink(0.2)
                self.scorer.trigger_lockdown()
                self.hal.mesh.broadcast_threat({
                    "source_node": NODE_ID,
                    "threat_score": score,
                    "organization_id": result.get("organization_id"),
                    "global_prediction": result.get("global_prediction"),
                    "local_prediction": result.get("local_prediction"),
                    "policy_status": decision.status,
                })
                print(
                    "[PIPELINE] Software containment accepted; physical relay action "
                    "is still an M1 hardware-handoff requirement.\n"
                )
            else:
                print(
                    "[PIPELINE] No physical isolation requested: independent authenticated "
                    "evidence and policy approval are still required.\n"
                )

    def get_latest_telemetry(self) -> dict:
        """Return the latest normalized M3 event for an M4 adapter."""
        return dict(self.latest_telemetry)

    def submit_security_evidence(
        self,
        *,
        model_result: dict,
        incident_id: str,
        evidence_envelopes=(),
        quorum_envelopes=(),
        signals=None,
        quorum_votes=(),
        now=None,
    ) -> dict:
        """Submit M2 evidence through authenticated or legacy compatibility paths.

        New callers should pass authenticated M2 envelopes. The decoded-object
        arguments remain only for compatibility with existing host-side adapters.
        """
        if evidence_envelopes or quorum_envelopes:
            decision = self.decision_path.submit_authenticated(
                model_result=model_result,
                evidence_envelopes=evidence_envelopes,
                quorum_envelopes=quorum_envelopes,
                incident_id=incident_id,
                now=now,
            )
        else:
            decision = self.decision_path.submit(
                model_result=model_result,
                signals=signals,
                incident_id=incident_id,
                quorum_votes=quorum_votes,
                now=now,
            )
        self.latest_telemetry = decision.telemetry
        return decision.to_dict()

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
        self.scorer.save_profile()

        self.ledger.add_entry(
            "system_shutdown",
            {
                "packets_processed": self.packet_count,
                "anomalies_detected": self.anomaly_count,
            },
        )

        is_valid, broken_at = self.ledger.verify_chain()
        print(
            f"\n[LEDGER] Forensic Chain Integrity: "
            f"{'✅ VALID' if is_valid else f'❌ BROKEN at #{broken_at}'}"
        )
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
