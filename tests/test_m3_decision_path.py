import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "m3-ml-ledger" / "src"))

from authenticated_envelope import AuthenticatedEnvelope, ReplayProtector, SequenceAllocator
from ledger import HashChainLedger
from m3_decision_path import M3DecisionPath
from m3_security_contracts import EvidenceSignal
from normalized_telemetry import TELEMETRY_SCHEMA_VERSION, NormalizedTelemetry
from quorum_state import QuorumState, QuorumVote, VoteDecision


KEY = b"simulation-key-0123456789012345"


def model_result(anomaly: bool = True) -> dict:
    return {
        "state": "alert" if anomaly else "armed",
        "score": 0.92 if anomaly else 0.04,
        "probability_attack": 0.92 if anomaly else 0.04,
        "threshold": 0.55,
        "is_anomaly": anomaly,
        "global_prediction": "ATTACK" if anomaly else "BENIGN",
        "local_prediction": "ANOMALY" if anomaly else "NORMAL",
        "local_detection_enabled": True,
        "organization_id": "company_one",
        "profile_ready": True,
        "profile_samples": 2048,
        "feature_count": 45,
        "timestamp": "2026-08-24T10:00:00+00:00",
    }


def signals() -> list[EvidenceSignal]:
    return [
        EvidenceSignal("ml-1", "node-a", "ml-v3", "CONFIRM", True, True, 0.92),
        EvidenceSignal("peer-1", "node-b", "peer", "CONFIRM", True, True, 0.91),
    ]


def test_two_signal_slice_issues_receipt_without_configured_quorum(tmp_path):
    ledger = HashChainLedger(str(tmp_path / "ledger.json"))
    path = M3DecisionPath(
        ledger=ledger,
        node_id="node-a",
        organization_id="company_one",
        counter_path=tmp_path / "counter.txt",
    )

    result = path.submit(
        model_result=model_result(),
        signals=signals(),
        incident_id="incident-1",
        now=100.0,
    )

    assert result.status == "CONTAINMENT_ACCEPTED"
    assert result.receipt is not None
    assert result.telemetry["schema_version"] == TELEMETRY_SCHEMA_VERSION
    assert result.telemetry["quorum"]["state"] == "NOT_CONFIGURED"
    assert result.telemetry["actuation"]["relay_requested"] is True
    assert result.telemetry["actuation"]["relay_acknowledged"] is True
    assert result.telemetry["actuation"]["relay_verified"] is False
    assert result.telemetry["hardware"]["physical_controller_validated"] is False
    assert "private_key" not in str(result.telemetry)
    assert ledger.verify_chain() == (True, None)


def test_configured_quorum_requires_approved_votes(tmp_path):
    ledger = HashChainLedger(str(tmp_path / "ledger.json"))
    path = M3DecisionPath(
        ledger=ledger,
        node_id="node-a",
        organization_id="company_one",
        counter_path=tmp_path / "counter.txt",
        expected_voters=("node-a", "node-b", "node-c"),
        required_confirmations=2,
        quorum_deadline_seconds=10.0,
    )
    evidence = signals()
    digest = path.gate.evaluate("incident-2", evidence).evidence_digest
    votes = [
        QuorumVote("incident-2", "node-a", VoteDecision.CONFIRM, digest, 1, True, True, 101.0),
        QuorumVote("incident-2", "node-b", VoteDecision.CONFIRM, digest, 1, True, True, 102.0),
    ]

    result = path.submit(
        model_result=model_result(),
        signals=evidence,
        incident_id="incident-2",
        quorum_votes=votes,
        now=100.0,
    )

    assert result.status == "CONTAINMENT_ACCEPTED"
    assert result.telemetry["quorum"]["state"] == QuorumState.APPROVED.value
    assert result.controller["relay_state"] == "ISOLATED"


def test_one_signal_never_reaches_controller(tmp_path):
    ledger = HashChainLedger(str(tmp_path / "ledger.json"))
    path = M3DecisionPath(
        ledger=ledger,
        node_id="node-a",
        organization_id="company_one",
        counter_path=tmp_path / "counter.txt",
    )

    result = path.submit(
        model_result=model_result(),
        signals=signals()[:1],
        incident_id="incident-3",
        now=100.0,
    )

    assert result.status == "PENDING_EVIDENCE"
    assert result.receipt is None
    assert result.controller["relay_state"] == "CONNECTED"
    assert result.telemetry["actuation"]["relay_requested"] is False


def test_quorum_conflict_blocks_receipt(tmp_path):
    ledger = HashChainLedger(str(tmp_path / "ledger.json"))
    path = M3DecisionPath(
        ledger=ledger,
        node_id="node-a",
        organization_id="company_one",
        counter_path=tmp_path / "counter.txt",
        expected_voters=("node-a", "node-b", "node-c"),
        required_confirmations=2,
        quorum_deadline_seconds=10.0,
    )
    evidence = signals()
    digest = path.gate.evaluate("incident-4", evidence).evidence_digest
    votes = [
        QuorumVote("incident-4", "node-a", VoteDecision.CONFIRM, digest, 1, True, True, 101.0),
        QuorumVote("incident-4", "node-b", VoteDecision.DENY, digest, 1, True, True, 102.0),
    ]

    result = path.submit(
        model_result=model_result(),
        signals=evidence,
        incident_id="incident-4",
        quorum_votes=votes,
        now=100.0,
    )

    assert result.status == "PENDING_QUORUM"
    assert result.receipt is None
    assert result.telemetry["quorum"]["state"] == QuorumState.CONFLICT.value
    assert result.controller["relay_state"] == "CONNECTED"


def test_authenticated_envelope_replay_is_rejected_at_m3_boundary(tmp_path):
    ledger = HashChainLedger(str(tmp_path / "ledger.json"))
    path = M3DecisionPath(
        ledger=ledger,
        node_id="node-a",
        organization_id="company_one",
        counter_path=tmp_path / "counter.txt",
        replay_protector=ReplayProtector(max_age_seconds=30, future_skew_seconds=5),
    )
    envelope = AuthenticatedEnvelope.create(
        sender_id="node-a",
        recipient="m3",
        message_type="ML_EVIDENCE",
        sequence=SequenceAllocator().next(),
        payload={"incident_id": "incident-5"},
        key=KEY,
        key_id="sim-node-a",
        key_epoch=1,
        timestamp=100.0,
    )

    assert path.accept_authenticated_envelope(envelope, KEY, now=100.0) is True
    assert path.accept_authenticated_envelope(envelope, KEY, now=100.0) is False


def test_telemetry_rejects_secret_like_fields():
    with pytest.raises(ValueError, match="secret-like"):
        NormalizedTelemetry(
            event_type="TEST",
            timestamp="now",
            organization_id="org",
            node_id="node",
            incident_id="incident",
            evidence={"private_key": "should-never-appear"},
        ).to_dict()


def _envelope(sender, message_type, sequence, payload):
    return AuthenticatedEnvelope.create(
        sender_id=sender,
        recipient="m3",
        message_type=message_type,
        sequence=sequence,
        payload=payload,
        key=KEY,
        key_id=f"sim-{sender}",
        key_epoch=1,
        timestamp=100.0,
    )


def test_authenticated_envelopes_feed_m3_evidence_and_quorum(tmp_path):
    ledger = HashChainLedger(str(tmp_path / "ledger.json"))
    path = M3DecisionPath(
        ledger=ledger,
        node_id="node-a",
        organization_id="company_one",
        counter_path=tmp_path / "counter.txt",
        expected_voters=("node-a", "node-b"),
        required_confirmations=2,
        quorum_deadline_seconds=10.0,
    )
    evidence_payloads = [
        {"signal_id": "ml-1", "signal_type": "ml-v3", "decision": "CONFIRM", "confidence": 0.92},
        {"signal_id": "peer-1", "signal_type": "peer", "decision": "CONFIRM", "confidence": 0.91},
    ]
    evidence_envelopes = [
        (_envelope("node-a", "ML_EVIDENCE", 1, evidence_payloads[0]), KEY),
        (_envelope("node-b", "PEER_EVIDENCE", 1, evidence_payloads[1]), KEY),
    ]
    expected_signals = [
        EvidenceSignal("ml-1", "node-a", "ml-v3", "CONFIRM", True, True, 0.92),
        EvidenceSignal("peer-1", "node-b", "peer", "CONFIRM", True, True, 0.91),
    ]
    digest = path.gate.evaluate("incident-auth", expected_signals).evidence_digest
    quorum_envelopes = [
        (
            _envelope(
                "node-a",
                "QUORUM_VOTE",
                2,
                {"incident_id": "incident-auth", "decision": "CONFIRM", "evidence_digest": digest},
            ),
            KEY,
        ),
        (
            _envelope(
                "node-b",
                "QUORUM_VOTE",
                2,
                {"incident_id": "incident-auth", "decision": "CONFIRM", "evidence_digest": digest},
            ),
            KEY,
        ),
    ]

    result = path.submit_authenticated(
        model_result=model_result(),
        evidence_envelopes=evidence_envelopes,
        quorum_envelopes=quorum_envelopes,
        incident_id="incident-auth",
        now=100.0,
    )

    assert result.status == "CONTAINMENT_ACCEPTED"
    assert result.telemetry["quorum"]["state"] == QuorumState.APPROVED.value
    assert result.telemetry["receipt"]["signature_verified"] is True
