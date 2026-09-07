import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "m2-systems" / "src"))
sys.path.insert(0, str(ROOT / "m3-ml-ledger" / "src"))

from authenticated_envelope import AuthenticatedEnvelope
from evidence_transport import (
    M2EvidenceTransport,
    derive_signing_key,
    load_or_create_node_key,
)
from m3_security_contracts import TwoSignalGate
from quorum_state import QuorumState, QuorumStateMachine, VoteDecision

KEY = b"m2-evidence-transport-test-key0"


def make_transport(sender_id="node-a", **kwargs):
    return M2EvidenceTransport(sender_id=sender_id, key=KEY, key_id=f"{sender_id}-key", **kwargs)


# ── Signal-level gating ──────────────────────────────────────────────────

def test_signal_valid_is_authenticated():
    t = make_transport()
    signal = t.submit_signal(
        signal_id="sig-1", source_id="known-detector", signal_type="known_attack",
        decision="CONFIRM", timestamp=100.0, now=100.0,
    )
    assert signal.authenticated is True and signal.fresh is True


def test_signal_stale_is_rejected():
    t = make_transport(max_age_seconds=30.0)
    signal = t.submit_signal(
        signal_id="sig-2", source_id="known-detector", signal_type="known_attack",
        decision="CONFIRM", timestamp=1.0, now=1000.0,
    )
    assert signal.authenticated is False and signal.fresh is False


def test_signal_replayed_is_rejected_on_second_submission():
    t = make_transport()
    envelope = t.build_signal_envelope(
        signal_id="sig-3", source_id="known-detector", signal_type="known_attack",
        decision="CONFIRM", sequence=1, timestamp=100.0,
    )
    first = t.authenticate_signal(envelope, now=100.0)
    second = t.authenticate_signal(envelope, now=100.0)
    assert first.authenticated is True
    assert second.authenticated is False


def test_signal_invalid_mac_is_rejected():
    t = make_transport()
    envelope = t.build_signal_envelope(
        signal_id="sig-4", source_id="known-detector", signal_type="known_attack",
        decision="CONFIRM", sequence=1, timestamp=100.0,
    )
    tampered = AuthenticatedEnvelope.from_dict(
        {**envelope.to_dict(), "payload": {**envelope.payload, "decision": "DENY"}}
    )
    signal = t.authenticate_signal(tampered, now=100.0)
    assert signal.authenticated is False


def test_signal_out_of_order_is_rejected():
    t = make_transport()
    high = t.build_signal_envelope(
        signal_id="sig-5a", source_id="known-detector", signal_type="known_attack",
        decision="CONFIRM", sequence=5, timestamp=100.0,
    )
    low = t.build_signal_envelope(
        signal_id="sig-5b", source_id="known-detector", signal_type="known_attack",
        decision="CONFIRM", sequence=3, timestamp=100.0,
    )
    assert t.authenticate_signal(high, now=100.0).authenticated is True
    assert t.authenticate_signal(low, now=100.0).authenticated is False


# ── Vote-level gating ─────────────────────────────────────────────────────

def test_vote_valid_is_authenticated():
    t = make_transport()
    vote = t.submit_vote(
        incident_id="incident-1", voter_id="node-a", decision=VoteDecision.CONFIRM,
        evidence_digest="a" * 64, vote_sequence=1, timestamp=100.0, received_at=100.0,
    )
    assert vote.authenticated is True and vote.fresh is True


def test_vote_stale_is_rejected():
    t = make_transport(max_age_seconds=30.0)
    vote = t.submit_vote(
        incident_id="incident-2", voter_id="node-a", decision=VoteDecision.CONFIRM,
        evidence_digest="a" * 64, vote_sequence=1, timestamp=1.0, received_at=1000.0,
    )
    assert vote.authenticated is False and vote.fresh is False


def test_vote_replayed_is_rejected_on_second_submission():
    t = make_transport()
    envelope = t.build_vote_envelope(
        incident_id="incident-3", voter_id="node-a", decision=VoteDecision.CONFIRM,
        evidence_digest="a" * 64, vote_sequence=1, sequence=1, timestamp=100.0,
    )
    first = t.authenticate_vote(envelope, received_at=100.0, now=100.0)
    second = t.authenticate_vote(envelope, received_at=101.0, now=101.0)
    assert first.authenticated is True
    assert second.authenticated is False


def test_vote_invalid_mac_is_rejected():
    t = make_transport()
    envelope = t.build_vote_envelope(
        incident_id="incident-4", voter_id="node-a", decision=VoteDecision.CONFIRM,
        evidence_digest="a" * 64, vote_sequence=1, sequence=1, timestamp=100.0,
    )
    tampered = AuthenticatedEnvelope.from_dict(
        {**envelope.to_dict(), "payload": {**envelope.payload, "decision": "DENY"}}
    )
    vote = t.authenticate_vote(tampered, received_at=100.0, now=100.0)
    assert vote.authenticated is False


def test_vote_out_of_order_is_rejected():
    t = make_transport()
    high = t.build_vote_envelope(
        incident_id="incident-5", voter_id="node-a", decision=VoteDecision.CONFIRM,
        evidence_digest="a" * 64, vote_sequence=1, sequence=5, timestamp=100.0,
    )
    low = t.build_vote_envelope(
        incident_id="incident-5", voter_id="node-a", decision=VoteDecision.CONFIRM,
        evidence_digest="a" * 64, vote_sequence=2, sequence=3, timestamp=100.0,
    )
    assert t.authenticate_vote(high, received_at=100.0, now=100.0).authenticated is True
    assert t.authenticate_vote(low, received_at=101.0, now=101.0).authenticated is False


# ── Integration: confirm M3's gate/state-machine reacts correctly ────────

def test_two_signal_gate_approves_only_with_two_authenticated_independent_signals():
    t = make_transport()
    good = t.submit_signal(
        signal_id="sig-i1", source_id="known-detector", signal_type="known_attack",
        decision="CONFIRM", timestamp=100.0, now=100.0,
    )
    stale = t.submit_signal(
        signal_id="sig-i2", source_id="adaptive-profile", signal_type="adaptive_anomaly",
        decision="CONFIRM", timestamp=1.0, now=1000.0,
    )
    gate = TwoSignalGate()
    assert gate.evaluate("incident-int-1", [good, stale]).approved is False

    good2 = t.submit_signal(
        signal_id="sig-i3", source_id="adaptive-profile", signal_type="adaptive_anomaly",
        decision="CONFIRM", timestamp=100.0, now=100.0,
    )
    assert gate.evaluate("incident-int-1", [good, good2]).approved is True


def test_quorum_state_machine_rejects_unauthenticated_vote_and_logs_it():
    t = make_transport()
    quorum = QuorumStateMachine()
    quorum.start(
        incident_id="incident-int-2", evidence_digest="b" * 64,
        expected_voters=["node-a", "node-b"], required_confirmations=2,
        started_at=100.0, deadline_seconds=10.0,
    )
    envelope = t.build_vote_envelope(
        incident_id="incident-int-2", voter_id="node-a", decision=VoteDecision.CONFIRM,
        evidence_digest="b" * 64, vote_sequence=1, sequence=1, timestamp=100.0,
    )
    t.authenticate_vote(envelope, received_at=100.0, now=100.0)
    replayed = t.authenticate_vote(envelope, received_at=101.0, now=101.0)
    state = quorum.add_vote(replayed)
    assert state == QuorumState.COLLECTING
    assert quorum.snapshot("incident-int-2")["rejected_votes"][0]["reason"] == "unauthenticated_or_stale"


def test_quorum_state_machine_approves_with_two_authenticated_confirm_votes():
    quorum = QuorumStateMachine()
    quorum.start(
        incident_id="incident-int-3", evidence_digest="c" * 64,
        expected_voters=["node-a", "node-b"], required_confirmations=2,
        started_at=100.0, deadline_seconds=10.0,
    )
    t_a = make_transport(sender_id="node-a")
    t_b = make_transport(sender_id="node-b")
    vote_a = t_a.submit_vote(
        incident_id="incident-int-3", voter_id="node-a", decision=VoteDecision.CONFIRM,
        evidence_digest="c" * 64, vote_sequence=1, timestamp=100.0, received_at=100.0,
    )
    vote_b = t_b.submit_vote(
        incident_id="incident-int-3", voter_id="node-b", decision=VoteDecision.CONFIRM,
        evidence_digest="c" * 64, vote_sequence=1, timestamp=101.0, received_at=101.0,
    )
    assert vote_a.authenticated is True
    assert vote_b.authenticated is True
    quorum.add_vote(vote_a)
    state = quorum.add_vote(vote_b)
    assert state == QuorumState.APPROVED


def test_shared_sequence_space_spans_signal_and_vote_submission():
    """One transport, mixed message types: signal(seq=5), vote(seq=3), signal(seq=6).

    ReplayProtector.accept()'s dedup key is (sender_id, key_epoch) only
    (authenticated_envelope.py:212) -- no message_type. So a vote sequence
    lower than an already-accepted signal's sequence, from the same
    transport, must be rejected as out-of-order: this is the empirical
    proof that M2EvidenceTransport's shared ReplayProtector/SequenceAllocator
    design actually matters, not just a reasonable-sounding choice.
    """
    t = make_transport()
    signal_envelope = t.build_signal_envelope(
        signal_id="sig-shared-1", source_id="known-detector", signal_type="known_attack",
        decision="CONFIRM", sequence=5, timestamp=100.0,
    )
    signal = t.authenticate_signal(signal_envelope, now=100.0)
    assert signal.authenticated is True

    vote_envelope = t.build_vote_envelope(
        incident_id="incident-shared-1", voter_id="node-a", decision=VoteDecision.CONFIRM,
        evidence_digest="d" * 64, vote_sequence=1, sequence=3, timestamp=100.0,
    )
    vote = t.authenticate_vote(vote_envelope, received_at=100.0, now=100.0)
    assert vote.authenticated is False  # seq=3 <= 5, rejected as out-of-order across types

    signal_envelope_2 = t.build_signal_envelope(
        signal_id="sig-shared-2", source_id="known-detector", signal_type="known_attack",
        decision="CONFIRM", sequence=6, timestamp=100.0,
    )
    signal_2 = t.authenticate_signal(signal_envelope_2, now=100.0)
    assert signal_2.authenticated is True  # seq=6 > 5, accepted; 3's rejection didn't advance the counter


# ── Per-node key provisioning (B2 resolution) ────────────────────────────

def test_two_sender_ids_produce_genuinely_different_signing_keys(tmp_path):
    master_a = load_or_create_node_key("node-a", keys_dir=tmp_path)
    master_b = load_or_create_node_key("node-b", keys_dir=tmp_path)
    assert master_a != master_b

    signing_a = derive_signing_key(master_a, key_epoch=1)
    signing_b = derive_signing_key(master_b, key_epoch=1)
    assert signing_a != signing_b


def test_same_sender_id_different_key_epoch_produces_different_derived_key():
    master = b"x" * 32
    key_epoch_1 = derive_signing_key(master, key_epoch=1)
    key_epoch_2 = derive_signing_key(master, key_epoch=2)
    assert key_epoch_1 != key_epoch_2


def test_node_key_is_write_once_if_absent(tmp_path):
    first = load_or_create_node_key("node-a", keys_dir=tmp_path)
    second = load_or_create_node_key("node-a", keys_dir=tmp_path)
    assert first == second
    assert (tmp_path / "node-a.key").exists()


def test_two_auto_derived_transports_cannot_verify_each_others_envelopes(tmp_path):
    t_a = M2EvidenceTransport(sender_id="node-a", key_epoch=1, keys_dir=tmp_path)
    t_b = M2EvidenceTransport(sender_id="node-b", key_epoch=1, keys_dir=tmp_path)
    assert t_a.key != t_b.key

    envelope = t_a.build_signal_envelope(
        signal_id="sig-forge-1", source_id="known-detector", signal_type="known_attack",
        decision="CONFIRM", timestamp=100.0,
    )
    forged = t_a.authenticate_signal(envelope, verify_key=t_b.key, now=100.0)
    assert forged.authenticated is False


def test_shared_sequence_space_still_holds_with_auto_derived_key(tmp_path):
    """Re-proves the item-4 constraint under the NEW key-derivation path,
    not just the pre-existing explicit-key path (already re-confirmed by
    test_shared_sequence_space_spans_signal_and_vote_submission passing
    unchanged)."""
    t = M2EvidenceTransport(sender_id="node-c", key_epoch=1, keys_dir=tmp_path)
    signal_envelope = t.build_signal_envelope(
        signal_id="sig-auto-1", source_id="known-detector", signal_type="known_attack",
        decision="CONFIRM", sequence=5, timestamp=100.0,
    )
    assert t.authenticate_signal(signal_envelope, now=100.0).authenticated is True

    vote_envelope = t.build_vote_envelope(
        incident_id="incident-auto-1", voter_id="node-c", decision=VoteDecision.CONFIRM,
        evidence_digest="e" * 64, vote_sequence=1, sequence=3, timestamp=100.0,
    )
    assert t.authenticate_vote(vote_envelope, received_at=100.0, now=100.0).authenticated is False
