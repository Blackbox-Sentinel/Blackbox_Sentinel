"""M2-owned authenticated transport for evidence signals and quorum votes.

Reuses the AuthenticatedEnvelope/ReplayProtector pattern from
integration/phase2_vertical_slice.py's M2SimTransport (:46-80), corrected
for M2-2/M2-3:
- wraps the actual EvidenceSignal/QuorumVote payload via .to_dict()-shaped
  fields (m3_security_contracts.py:88-98, quorum_state.py:81-91), not
  NormalizedTelemetry;
- gates on ReplayProtector.accept()'s real result: a rejected envelope
  produces authenticated=False, fresh=False, not a scripted label with
  the message passed through as if verified.

Still a software simulation of the transport boundary (no ESP32/physical
link) -- but unlike M2SimTransport this authenticates the evidence/vote
objects themselves, which is the actual M2-2/M2-3 ownership per
docs/Phase2_Vertical_Slice.md's team-ownership section.

Signals and votes share one ReplayProtector/SequenceAllocator per
transport instance. This is required, not stylistic: ReplayProtector's
dedup key is (sender_id, key_epoch) only (authenticated_envelope.py:212)
-- it has no message_type component -- so a real downstream verifier
keyed the same way would see signal and vote sequence numbers from the
same sender in one shared space regardless of which object type sent
them.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
M3_SRC = ROOT / "m3-ml-ledger" / "src"
if str(M3_SRC) not in sys.path:
    sys.path.insert(0, str(M3_SRC))

from authenticated_envelope import AuthenticatedEnvelope, ReplayProtector, SequenceAllocator  # noqa: E402
from m3_security_contracts import EvidenceSignal  # noqa: E402
from quorum_state import QuorumVote, VoteDecision  # noqa: E402


# Per-node key provisioning (B2 resolution: per-node, not shared mesh-wide or
# per-pair -- see B2_Crypto_Shortlist.md secs 2b/4, GAP_Shared_Quorum_Key.md).
# Mirrors security/trusted_controller.py's load_or_create_shared_secret()
# exactly (write-once-if-absent, 32 random bytes), keyed per sender_id
# instead of one shared file.
DEFAULT_KEYS_DIR = ROOT / "m3-ml-ledger" / "data" / "keys"


def load_or_create_node_key(sender_id: str, keys_dir: Path | str | None = None) -> bytes:
    """Load sender_id's master key, generating it once if absent.

    Same mechanism as security/trusted_controller.py's
    load_or_create_shared_secret(): write-once-if-absent, 32 random bytes,
    read back from disk. One file per node, not one shared file.
    """
    base = Path(keys_dir) if keys_dir is not None else DEFAULT_KEYS_DIR
    key_path = base / f"{sender_id}.key"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if not key_path.exists():
        key_path.write_bytes(secrets.token_bytes(32))
    return key_path.read_bytes()


def derive_signing_key(master_key: bytes, key_epoch: int) -> bytes:
    """signing_key = HMAC(master_key, key_epoch), per the approved B2 resolution.

    One master key per node covers all future epochs; rotation is
    incrementing key_epoch, no redistribution required. key_epoch is
    encoded as its decimal string (readable/debuggable, unambiguous for
    the non-negative integers key_epoch is validated to, matching this
    codebase's general preference for string/JSON canonical encodings
    over raw binary packing -- see authenticated_envelope.py's
    _canonical_json).
    """
    return hmac.new(master_key, str(key_epoch).encode("utf-8"), hashlib.sha256).digest()


class M2EvidenceTransport:
    """Authenticated outbound channel for one M2 node's signals and votes."""

    def __init__(
        self,
        *,
        sender_id: str,
        key: bytes | None = None,
        key_id: str | None = None,
        key_epoch: int = 1,
        max_age_seconds: float = 30.0,
        future_skew_seconds: float = 5.0,
        keys_dir: Path | str | None = None,
    ) -> None:
        self.sender_id = sender_id
        self.key_epoch = key_epoch
        if key is None:
            # No explicit key: derive this node's own signing key instead of
            # requiring a caller-supplied shared constant.
            master_key = load_or_create_node_key(sender_id, keys_dir)
            key = derive_signing_key(master_key, key_epoch)
        self.key = key
        self.key_id = key_id if key_id is not None else f"{sender_id}-epoch-{key_epoch}"
        # Shared across signals and votes deliberately: ReplayProtector.accept()'s
        # dedup key is identity = (envelope.sender_id, envelope.key_epoch) only
        # (authenticated_envelope.py:212) -- message_type is never read there.
        # Confirmed by test: a vote sequence lower than an already-accepted
        # signal's sequence from the same transport is rejected as out-of-order
        # (tests/test_evidence_transport.py::test_shared_sequence_space_spans_signal_and_vote_submission).
        self.sequence = SequenceAllocator()
        self.replay_protector = ReplayProtector(
            max_age_seconds=max_age_seconds, future_skew_seconds=future_skew_seconds
        )

    # ── Evidence signals (M2-2) ──────────────────────────────────────────

    def build_signal_envelope(
        self,
        *,
        signal_id: str,
        source_id: str,
        signal_type: str,
        decision: str,
        confidence: float | None = None,
        details: Mapping[str, Any] | None = None,
        sequence: int | None = None,
        timestamp: float | None = None,
    ) -> AuthenticatedEnvelope:
        payload = {
            "signal_id": signal_id,
            "source_id": source_id,
            "signal_type": signal_type,
            "decision": decision,
            "confidence": confidence,
            "details": dict(details or {}),
        }
        return AuthenticatedEnvelope.create(
            sender_id=self.sender_id,
            recipient="m3-evidence-gate",
            message_type="EVIDENCE_SIGNAL",
            sequence=sequence if sequence is not None else self.sequence.next(),
            payload=payload,
            key=self.key,
            key_id=self.key_id,
            key_epoch=self.key_epoch,
            timestamp=timestamp,
        )

    def authenticate_signal(
        self,
        envelope: AuthenticatedEnvelope,
        *,
        verify_key: bytes | None = None,
        now: float | None = None,
    ) -> EvidenceSignal:
        """Gate on ReplayProtector.accept(): only True/True on real acceptance."""
        accepted = self.replay_protector.accept(
            envelope, verify_key if verify_key is not None else self.key, now=now
        )
        payload = envelope.payload
        return EvidenceSignal(
            signal_id=payload["signal_id"],
            source_id=payload["source_id"],
            signal_type=payload["signal_type"],
            decision=payload["decision"],
            authenticated=accepted,
            fresh=accepted,
            confidence=payload.get("confidence"),
            details=payload.get("details"),
        )

    def submit_signal(self, *, now: float | None = None, **kwargs: Any) -> EvidenceSignal:
        """Production path: build + authenticate a fresh signal in one call."""
        envelope = self.build_signal_envelope(**kwargs)
        return self.authenticate_signal(envelope, now=now)

    # ── Quorum votes (M2-3) ──────────────────────────────────────────────

    def build_vote_envelope(
        self,
        *,
        incident_id: str,
        voter_id: str,
        decision: VoteDecision,
        evidence_digest: str,
        vote_sequence: int,
        sequence: int | None = None,
        timestamp: float | None = None,
    ) -> AuthenticatedEnvelope:
        payload = {
            "incident_id": incident_id,
            "voter_id": voter_id,
            "decision": decision.value,
            "evidence_digest": evidence_digest,
            "vote_sequence": vote_sequence,
        }
        return AuthenticatedEnvelope.create(
            sender_id=self.sender_id,
            recipient="m3-quorum",
            message_type="QUORUM_VOTE",
            sequence=sequence if sequence is not None else self.sequence.next(),
            payload=payload,
            key=self.key,
            key_id=self.key_id,
            key_epoch=self.key_epoch,
            timestamp=timestamp,
        )

    def authenticate_vote(
        self,
        envelope: AuthenticatedEnvelope,
        *,
        received_at: float,
        verify_key: bytes | None = None,
        now: float | None = None,
    ) -> QuorumVote:
        """Gate on ReplayProtector.accept(): only True/True on real acceptance."""
        accepted = self.replay_protector.accept(
            envelope, verify_key if verify_key is not None else self.key, now=now
        )
        payload = envelope.payload
        return QuorumVote(
            incident_id=payload["incident_id"],
            voter_id=payload["voter_id"],
            decision=VoteDecision(payload["decision"]),
            evidence_digest=payload["evidence_digest"],
            sequence=payload["vote_sequence"],
            authenticated=accepted,
            fresh=accepted,
            received_at=received_at,
        )

    def submit_vote(self, *, received_at: float, now: float | None = None, **kwargs: Any) -> QuorumVote:
        """Production path: build + authenticate a fresh vote in one call."""
        envelope = self.build_vote_envelope(**kwargs)
        return self.authenticate_vote(
            envelope, received_at=received_at, now=now if now is not None else received_at
        )


__all__ = ["M2EvidenceTransport"]
