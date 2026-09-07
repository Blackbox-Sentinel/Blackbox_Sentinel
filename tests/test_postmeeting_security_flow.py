import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "m3-ml-ledger" / "src"))

from authenticated_envelope import AuthenticatedEnvelope, ReplayProtector, SequenceAllocator
from ledger import HashChainLedger
from m3_security_contracts import (
    ContainmentReceiptService,
    Ed25519ReceiptSigner,
    EvidenceSignal,
    SoftwareMonotonicCounter,
    TwoSignalGate,
)
from quorum_state import QuorumState, QuorumStateMachine, QuorumVote, VoteDecision
from trusted_controller_sim import SimTrustedController


KEY = b"simulation-key-0123456789012345"


def digest_incident(incident_id: str) -> str:
    return hashlib.sha256(incident_id.encode("utf-8")).hexdigest()


def test_authenticated_envelope_rejects_replay_and_tampering():
    sequence = SequenceAllocator()
    envelope = AuthenticatedEnvelope.create(
        sender_id="node-a",
        recipient="controller",
        message_type="ML_EVIDENCE",
        sequence=sequence.next(),
        payload={"incident_id": "node-a:1", "attack": True},
        key=KEY,
        key_id="sim-node-a",
        key_epoch=1,
        timestamp=100.0,
    )
    protector = ReplayProtector(max_age_seconds=30, future_skew_seconds=5)
    assert protector.accept(envelope, KEY, now=100.0) is True
    assert protector.accept(envelope, KEY, now=100.0) is False

    tampered = AuthenticatedEnvelope.from_dict(
        {**envelope.to_dict(), "payload": {"incident_id": "node-a:2", "attack": True}}
    )
    assert protector.accept(tampered, KEY, now=100.0) is False


def test_quorum_receipt_and_controller_flow(tmp_path):
    evidence_digest = digest_incident("node-a:1")
    quorum = QuorumStateMachine()
    incident = quorum.start(
        incident_id="node-a:1",
        evidence_digest=evidence_digest,
        expected_voters=["node-a", "node-b", "node-c"],
        required_confirmations=2,
        started_at=100.0,
        deadline_seconds=10.0,
    )
    assert incident.state == QuorumState.COLLECTING

    assert quorum.add_vote(
        QuorumVote(
            incident_id="node-a:1",
            voter_id="node-a",
            decision=VoteDecision.CONFIRM,
            evidence_digest=evidence_digest,
            sequence=1,
            authenticated=True,
            fresh=True,
            received_at=101.0,
        )
    ) == QuorumState.COLLECTING
    assert quorum.add_vote(
        QuorumVote(
            incident_id="node-a:1",
            voter_id="node-b",
            decision=VoteDecision.CONFIRM,
            evidence_digest=evidence_digest,
            sequence=1,
            authenticated=True,
            fresh=True,
            received_at=102.0,
        )
    ) == QuorumState.APPROVED

    gate = TwoSignalGate()
    decision = gate.evaluate(
        "node-a:1",
        [
            EvidenceSignal("ml-1", "node-a", "ml", "CONFIRM", True, True, 0.98),
            EvidenceSignal("peer-1", "node-b", "peer", "CONFIRM", True, True, 0.91),
        ],
    )
    assert decision.approved is True

    ledger = HashChainLedger(str(tmp_path / "ledger.json"))
    receipt_service = ContainmentReceiptService(
        ledger=ledger,
        counter=SoftwareMonotonicCounter(tmp_path / "counter.txt"),
        signer=Ed25519ReceiptSigner(),
        controller_id="sim-controller",
    )
    receipt = receipt_service.issue(
        decision=decision,
        organization_id="company_one",
        key_epoch=1,
        quorum={"state": quorum.snapshot("node-a:1")["state"], "required": 2, "received": 2},
    )

    controller = SimTrustedController("sim-controller")
    assert controller.direct_isolate() is False
    assert controller.apply_containment(
        receipt=receipt,
        quorum_state=QuorumState.APPROVED.value,
        expected_incident_id="node-a:1",
    ) is True
    assert controller.status().relay_state == "ISOLATED"
    assert ledger.verify_chain() == (True, None)


def test_quorum_conflict_never_approves():
    digest = digest_incident("node-a:2")
    quorum = QuorumStateMachine()
    quorum.start(
        incident_id="node-a:2",
        evidence_digest=digest,
        expected_voters=["node-a", "node-b", "node-c"],
        required_confirmations=2,
        started_at=200.0,
        deadline_seconds=10.0,
    )
    assert quorum.add_vote(
        QuorumVote("node-a:2", "node-a", VoteDecision.CONFIRM, digest, 1, True, True, 201.0)
    ) == QuorumState.COLLECTING
    assert quorum.add_vote(
        QuorumVote("node-a:2", "node-b", VoteDecision.DENY, digest, 1, True, True, 202.0)
    ) == QuorumState.CONFLICT
