"""Run the BlackBox Sentinel Phase 2 software vertical slice.

This runner is intentionally hardware-independent:
M2 transport simulation -> M3 authenticated evidence/quorum/receipt ->
M4 normalized telemetry JSONL. It does not claim ESP32 relay enforcement.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
M3_SRC = ROOT / "m3-ml-ledger" / "src"
if str(M3_SRC) not in sys.path:
    sys.path.insert(0, str(M3_SRC))
M2_SRC = ROOT / "m2-systems" / "src"
if str(M2_SRC) not in sys.path:
    sys.path.insert(0, str(M2_SRC))

from authenticated_envelope import AuthenticatedEnvelope, ReplayProtector, SequenceAllocator  # noqa: E402
from evidence_transport import M2EvidenceTransport  # noqa: E402

from ledger import HashChainLedger  # noqa: E402
from m3_security_contracts import (  # noqa: E402
    ContainmentReceiptService,
    Ed25519ReceiptSigner,
    EvidenceSignal,
    SoftwareMonotonicCounter,
    TwoSignalGate,
)
from quorum_state import QuorumState, QuorumStateMachine, QuorumVote, VoteDecision  # noqa: E402
from trusted_controller_sim import SimTrustedController  # noqa: E402

from integration.telemetry import (  # noqa: E402
    EventStatus,
    JsonlTelemetryWriter,
    NormalizedTelemetry,
)


TRANSPORT_KEY = b"phase2-transport-key-012345678901"


class M2SimTransport:
    """Local JSONL transport standing in for the M2 real transport boundary."""

    def __init__(self, writer: JsonlTelemetryWriter, listener: Callable[[NormalizedTelemetry], None] | None = None) -> None:
        self.writer = writer
        self.listener = listener
        self.sequence = SequenceAllocator()
        self.replay_protector = ReplayProtector(max_age_seconds=60.0, future_skew_seconds=5.0)

    def publish(self, telemetry: NormalizedTelemetry) -> NormalizedTelemetry:
        envelope = AuthenticatedEnvelope.create(
            sender_id=telemetry.source,
            recipient="m4-dashboard",
            message_type=telemetry.event_type,
            sequence=self.sequence.next(),
            payload=telemetry.to_dict(),
            key=TRANSPORT_KEY,
            key_id="phase2-sim-transport",
            key_epoch=1,
        )
        accepted = self.replay_protector.accept(envelope, TRANSPORT_KEY)
        payload = dict(envelope.payload)
        payload.update(
            {
                "transport_sender": envelope.sender_id,
                "transport_sequence": envelope.sequence,
                "transport_auth": "VERIFIED" if accepted else "FAILED",
                "freshness_status": "FRESH" if accepted else "REJECTED",
            }
        )
        normalized = NormalizedTelemetry.from_mapping(payload)
        self.writer.emit(normalized)
        if self.listener:
            self.listener(normalized)
        return normalized


class Phase2VerticalSlice:
    """Orchestrate one deterministic packet-to-dashboard software demo."""

    def __init__(self, output_path: str | Path, *, sleep_seconds: float = 0.0) -> None:
        self.output_path = Path(output_path)
        self.sleep_seconds = max(0.0, sleep_seconds)
        self.writer = JsonlTelemetryWriter(self.output_path)
        self.transport = M2SimTransport(self.writer)
        self.m2_transport = M2EvidenceTransport(
            sender_id="node-a",
            key=TRANSPORT_KEY,
            key_id="phase2-transport-key",
            key_epoch=1,
            max_age_seconds=60.0,
            future_skew_seconds=5.0,
        )
        self.m2_peer_transport = M2EvidenceTransport(
            sender_id="node-b",
            key=TRANSPORT_KEY,
            key_id="phase2-transport-key",
            key_epoch=1,
            max_age_seconds=60.0,
            future_skew_seconds=5.0,
        )
        self.packet_count = 0

        self.alert_count = 0
        self.event_counter = 0
        self.events: list[NormalizedTelemetry] = []
        self.incident_id = "node-a:phase2-001"
        self.evidence_digest = hashlib.sha256(self.incident_id.encode("utf-8")).hexdigest()
        self.controller = SimTrustedController("sim-controller")
        self.ledger_path = self.output_path.with_suffix(".ledger.json")
        self.counter_path = self.output_path.with_suffix(".counter")
        self.ledger = HashChainLedger(str(self.ledger_path))
        self.receipt_service = ContainmentReceiptService(
            ledger=self.ledger,
            counter=SoftwareMonotonicCounter(self.counter_path),
            signer=Ed25519ReceiptSigner(),
            controller_id="sim-controller",
        )
        self.quorum = QuorumStateMachine()

    def emit(self, **kwargs: Any) -> NormalizedTelemetry:
        self.event_counter += 1
        payload: dict[str, Any] = {
            "event_id": f"phase2-{self.event_counter:04d}",
            "packet_count": self.packet_count,
            "alert_count": self.alert_count,
            "incident_id": self.incident_id if kwargs.get("signals") or kwargs.get("incident_id") else None,
            "evidence_digest": self.evidence_digest if kwargs.get("signals") or kwargs.get("incident_id") else None,
            "source": "m2-transport-sim",
        }
        payload.update(kwargs)
        telemetry = NormalizedTelemetry(**payload)
        normalized = self.transport.publish(telemetry)
        self.events.append(normalized)
        if self.sleep_seconds:
            time.sleep(self.sleep_seconds)
        return normalized

    def run(self) -> list[NormalizedTelemetry]:
        self.events = []
        self.packet_count = 12
        self.emit(
            event_type="calibration_completed",
            status=EventStatus.NORMAL.value,
            controller_state="ARMED",
            model_profile="phase2-calibration-sim",
            notes="Calibration window represented by deterministic software sample.",
        )
        self.packet_count += 8
        self.emit(
            event_type="normal_traffic",
            status=EventStatus.NORMAL.value,
            controller_state="ARMED",
            link_state="HEALTHY",
            relay_state="CONNECTED",
            relay_acknowledged=True,
            relay_verified=False,
            notes="Normal packet window received from M2 simulation.",
        )

        signal_a = self.m2_transport.submit_signal(
            signal_id="signal-known-001",
            source_id="known-detector",
            signal_type="known_attack",
            decision="CONFIRM",
            confidence=0.98,
            details={"score": -0.115, "transport": "M2EvidenceTransport"},
            timestamp=100.0,
            now=100.0,
        )
        signal_b = self.m2_peer_transport.submit_signal(
            signal_id="signal-adaptive-001",
            source_id="adaptive-profile",
            signal_type="adaptive_anomaly",
            decision="CONFIRM",
            confidence=0.91,
            details={"score": -0.115, "transport": "M2EvidenceTransport"},
            timestamp=100.0,
            now=100.0,
        )

        self.alert_count = 1
        self.emit(
            event_type="evidence_pending",
            status=EventStatus.PENDING.value,
            controller_state="ALERT_PENDING",
            signals=[signal_a.to_dict()],
            decision="WAITING",
            relay_state="CONNECTED",
            relay_acknowledged=True,
            quorum_state=QuorumState.COLLECTING.value,
            quorum_required=2,
            quorum_received=1,
            notes="One authenticated fresh signal received; waiting for independent evidence.",
        )

        gate = TwoSignalGate()
        decision = gate.evaluate(self.incident_id, [signal_a, signal_b])
        self.evidence_digest = decision.evidence_digest

        self.quorum.start(
            incident_id=self.incident_id,
            evidence_digest=self.evidence_digest,
            expected_voters=["node-a", "node-b", "node-c"],
            required_confirmations=2,
            started_at=100.0,
            deadline_seconds=10.0,
        )
        first_vote = self.m2_transport.submit_vote(
            incident_id=self.incident_id,
            voter_id="node-a",
            decision=VoteDecision.CONFIRM,
            evidence_digest=self.evidence_digest,
            vote_sequence=1,
            received_at=101.0,
            timestamp=101.0,
            now=101.0,
        )
        second_vote = self.m2_peer_transport.submit_vote(
            incident_id=self.incident_id,
            voter_id="node-b",
            decision=VoteDecision.CONFIRM,
            evidence_digest=self.evidence_digest,
            vote_sequence=1,
            received_at=102.0,
            timestamp=102.0,
            now=102.0,
        )

        self.quorum.add_vote(first_vote)
        quorum_state = self.quorum.add_vote(second_vote)
        quorum_snapshot = self.quorum.snapshot(self.incident_id)
        receipt = self.receipt_service.issue(
            decision=decision,
            organization_id="company_one",
            key_epoch=1,
            quorum={
                "state": quorum_state.value,
                "required": 2,
                "received": 2,
                "incident_id": self.incident_id,
            },
        )
        contained = self.controller.apply_containment(
            receipt=receipt,
            quorum_state=quorum_state.value,
            expected_incident_id=self.incident_id,
        )
        self.emit(
            event_type="containment_decision",
            status=EventStatus.APPROVED.value if contained else EventStatus.REJECTED.value,
            controller_state="ISOLATED" if contained else "ALERT_PENDING",
            signals=[signal_a.to_dict(), signal_b.to_dict()],
            decision="CONTAIN" if contained else "WAITING",
            relay_requested="ISOLATE",
            relay_acknowledged=contained,
            relay_verified=False,
            relay_state="ISOLATED" if contained else "CONNECTED",
            quorum_state=quorum_state.value,
            quorum_required=2,
            quorum_received=2,
            quorum_votes=quorum_snapshot["votes"],
            receipt_status="VALID" if contained else "NOT_AVAILABLE",
            receipt_id=receipt["payload"].get("receipt_sequence") and f"receipt-{receipt['payload']['receipt_sequence']:06d}",
            receipt_sequence=receipt["payload"].get("receipt_sequence"),
            sms_status="MOCK_SENT" if contained else "NOT_SENT",
            notes="M2 transport carried two authenticated independent signals; M3 quorum and receipt approved the software containment decision.",
        )

        self.emit(
            event_type="transport_rejection",
            status=EventStatus.REPLAY.value,
            controller_state="ISOLATED",
            relay_state="ISOLATED",
            relay_acknowledged=True,
            rejection_reason="REPLAYED",
            receipt_status="VALID",
            receipt_sequence=receipt["payload"].get("receipt_sequence"),
            recovery_state="LOCKED",
            notes="A repeated sequence was rejected by the transport replay policy.",
        )
        self.emit(
            event_type="transport_rejection",
            status=EventStatus.STALE.value,
            controller_state="ISOLATED",
            relay_state="ISOLATED",
            relay_acknowledged=True,
            rejection_reason="STALE",
            receipt_status="VALID",
            receipt_sequence=receipt["payload"].get("receipt_sequence"),
            recovery_state="LOCKED",
            notes="An old authenticated envelope was rejected by the freshness policy.",
        )

        conflict = QuorumStateMachine()
        conflict_id = "node-a:phase2-conflict"
        conflict.start(
            incident_id=conflict_id,
            evidence_digest=self.evidence_digest,
            expected_voters=["node-a", "node-b"],
            required_confirmations=2,
            started_at=200.0,
            deadline_seconds=10.0,
        )
        conflict.add_vote(QuorumVote(conflict_id, "node-a", VoteDecision.CONFIRM, self.evidence_digest, 1, True, True, 201.0))
        conflict_state = conflict.add_vote(QuorumVote(conflict_id, "node-b", VoteDecision.DENY, self.evidence_digest, 1, True, True, 202.0))
        self.emit(
            event_type="quorum_conflict",
            status=EventStatus.CONFLICT.value,
            controller_state="ALERT_PENDING",
            decision="CONFLICT",
            quorum_state=conflict_state.value,
            quorum_required=2,
            quorum_received=2,
            quorum_votes=conflict.snapshot(conflict_id)["votes"],
            relay_state="CONNECTED",
            relay_acknowledged=True,
            rejection_reason="CONFLICTING_VOTES",
            notes="Mixed CONFIRM/DENY votes never approve containment.",
        )
        self.emit(
            event_type="receipt_audit",
            status=EventStatus.RECEIPT.value,
            controller_state="ISOLATED",
            relay_state="ISOLATED",
            relay_acknowledged=True,
            receipt_status="VALID",
            receipt_id=f"receipt-{receipt['payload']['receipt_sequence']:06d}",
            receipt_sequence=receipt["payload"].get("receipt_sequence"),
            evidence_digest=self.evidence_digest,
            notes="M4 audit view can verify the receipt signature and display its ledger binding.",
        )
        self.controller.require_recovery()
        self.emit(
            event_type="recovery_required",
            status=EventStatus.RECOVERY.value,
            controller_state="RECOVERY",
            relay_state="ISOLATED",
            relay_acknowledged=True,
            key_state="INVALIDATED_SIMULATION_ONLY",
            power_state="PRIMARY_SIMULATION_ONLY",
            receipt_status="VALID",
            receipt_id=f"receipt-{receipt['payload']['receipt_sequence']:06d}",
            receipt_sequence=receipt["payload"].get("receipt_sequence"),
            recovery_state="AUTHENTICATION_REQUIRED",
            notes="Recovery remains locked until the approved operator workflow authorizes restoration.",
        )
        return list(self.events)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BlackBox Sentinel Phase 2 software vertical slice")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "m3-ml-ledger" / "data" / "phase2_telemetry.jsonl",
        help="JSONL telemetry output consumed by the M4 dashboard",
    )
    parser.add_argument("--sleep", type=float, default=0.0, help="Delay between demo events in seconds")
    args = parser.parse_args()
    runner = Phase2VerticalSlice(args.output, sleep_seconds=args.sleep)
    runner.run()
    print(f"Phase 2 software slice complete: {args.output}")
    print("M2 transport -> M3 evidence/quorum/receipt -> M4 normalized telemetry")
    print("Hardware boundary: simulation only; ESP32 enforcement still requires M1 validation.")


if __name__ == "__main__":
    main()
