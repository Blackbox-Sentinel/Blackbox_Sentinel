import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "m3-ml-ledger" / "src"))

from ledger import HashChainLedger
from m3_security_contracts import (
    ContainmentReceiptService,
    Ed25519ReceiptSigner,
    EvidenceSignal,
    SoftwareMonotonicCounter,
    TwoSignalGate,
)


def signal(signal_id, source_id, signal_type, *, authenticated=True, fresh=True):
    return EvidenceSignal(
        signal_id=signal_id,
        source_id=source_id,
        signal_type=signal_type,
        decision="CONFIRM",
        authenticated=authenticated,
        fresh=fresh,
        confidence=0.95,
    )


def test_two_signal_gate_requires_independent_authenticated_fresh_signals():
    gate = TwoSignalGate(required_signals=2)

    one_signal = gate.evaluate("incident-1", [signal("s1", "node-a", "ml")])
    assert one_signal.approved is False

    same_source = gate.evaluate(
        "incident-1",
        [signal("s1", "node-a", "ml"), signal("s2", "node-a", "tamper")],
    )
    assert same_source.approved is False

    stale = gate.evaluate(
        "incident-1",
        [
            signal("s1", "node-a", "ml"),
            signal("s2", "node-b", "peer", fresh=False),
        ],
    )
    assert stale.approved is False

    approved = gate.evaluate(
        "incident-1",
        [signal("s1", "node-a", "ml"), signal("s2", "node-b", "peer")],
    )
    assert approved.approved is True
    assert len(approved.accepted_signals) == 2
    assert len(approved.evidence_digest) == 64


def test_signed_containment_receipt_is_ledger_bound_and_tamper_evident(tmp_path):
    ledger = HashChainLedger(str(tmp_path / "ledger.json"))
    counter = SoftwareMonotonicCounter(tmp_path / "counter.txt")
    signer = Ed25519ReceiptSigner()
    service = ContainmentReceiptService(
        ledger=ledger,
        counter=counter,
        signer=signer,
        controller_id="sim-controller",
    )
    decision = TwoSignalGate().evaluate(
        "node-a:17",
        [signal("s1", "node-a", "ml"), signal("s2", "node-b", "peer")],
    )

    receipt = service.issue(
        decision=decision,
        organization_id="company_one",
        key_epoch=3,
        quorum={"required": 2, "received": 2, "state": "APPROVED"},
    )

    assert receipt["payload"]["decision"] == "CONTAIN"
    assert receipt["payload"]["receipt_sequence"] == 1
    assert receipt["payload"]["organization_id"] == "company_one"
    assert ContainmentReceiptService.verify(receipt) is True
    assert ledger.verify_chain() == (True, None)
    assert [entry["event_type"] for entry in ledger.chain] == [
        "containment_decision",
        "containment_receipt",
    ]

    tampered = {
        "payload": {**receipt["payload"], "organization_id": "other_company"},
        "signature": receipt["signature"],
        "public_key": receipt["public_key"],
    }
    assert ContainmentReceiptService.verify(tampered) is False


def test_receipt_requires_approved_decision(tmp_path):
    service = ContainmentReceiptService(
        ledger=HashChainLedger(str(tmp_path / "ledger.json")),
        counter=SoftwareMonotonicCounter(tmp_path / "counter.txt"),
        signer=Ed25519ReceiptSigner(),
    )
    decision = TwoSignalGate().evaluate("incident-2", [signal("s1", "node-a", "ml")])
    with pytest.raises(ValueError, match="unapproved"):
        service.issue(decision, "company_one", 1, {"required": 2})
