"""Simulation model for the BlackBox Sentinel trusted security controller.

This module is an engineering scaffold for Phase 2 and patent-scope validation.
It is not a replacement for an ESP32/secure-MCU implementation. The real
controller must enforce the same policy outside the Python process.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


DEFAULT_SHARED_SECRET_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "m3-ml-ledger", "data", "controller_secret.bin"
)


def load_or_create_shared_secret(path: str | None = None) -> bytes:
    """Load the simulation-phase shared HMAC secret, generating it once if absent.

    Every in-process TrustedController instance must use the same secret to
    verify each other's signals/votes/receipts. This is a simulation-phase
    convenience, not a hardware-backed key-provisioning mechanism.
    """
    secret_path = os.path.abspath(path or DEFAULT_SHARED_SECRET_PATH)
    os.makedirs(os.path.dirname(secret_path), exist_ok=True)
    if not os.path.exists(secret_path):
        with open(secret_path, "wb") as f:
            f.write(secrets.token_bytes(32))
    with open(secret_path, "rb") as f:
        return f.read()


class ControllerState(str, Enum):
    SAFE = "SAFE"
    ARMED = "ARMED"
    ALERT_PENDING = "ALERT_PENDING"
    ISOLATED = "ISOLATED"
    TAMPERED = "TAMPERED"
    RECOVERY = "RECOVERY"


@dataclass(frozen=True)
class EvidenceSignal:
    signal_id: str
    event_id: str
    source: str
    signal_type: str
    sequence: int
    issued_at: float
    payload: dict[str, Any]
    payload_hash: str
    auth_tag: str


@dataclass(frozen=True)
class PeerVote:
    vote_id: str
    event_id: str
    peer_id: str
    decision: str
    sequence: int
    issued_at: float
    auth_tag: str


@dataclass
class DecisionReceipt:
    receipt_id: str
    event_id: str
    counter: int
    controller_state: str
    decision: str
    evidence_ids: list[str]
    vote_ids: list[str]
    relay_requested: str
    relay_acknowledged: str
    created_at: float
    receipt_hash: str
    auth_tag: str
    external_witness_status: str = "NOT_CONFIGURED"


class TrustedController:
    """Deterministic policy engine used by simulation and unit tests.

    Policy defaults to two independent signals plus an optional peer quorum.
    Signals are accepted only once, within the freshness window, and with a
    valid HMAC. The relay decision is produced by this controller object rather
    than by the GUI or the ML scorer directly.
    """

    def __init__(
        self,
        secret: bytes | None = None,
        *,
        required_signals: tuple[str, ...] = ("known_attack", "adaptive_anomaly"),
        quorum_required: int = 0,
        freshness_window_seconds: float = 30.0,
    ) -> None:
        self.secret = secret or secrets.token_bytes(32)
        self.required_signals = tuple(required_signals)
        self.quorum_required = max(0, int(quorum_required))
        self.freshness_window_seconds = float(freshness_window_seconds)
        self.state = ControllerState.SAFE
        self.relay_state = "ENGAGED"
        self.counter = 0
        self._next_sequence: dict[str, int] = {}
        self._highest_sequence: dict[str, int] = {}
        self._signals: dict[str, EvidenceSignal] = {}
        self._votes: dict[str, PeerVote] = {}
        self.receipts: list[DecisionReceipt] = []
        self.events: list[dict[str, Any]] = []

    def arm(self) -> None:
        """Enter the normal monitoring state after calibration."""
        self.state = ControllerState.ARMED
        self.events.append({"event_type": "controller_state", "state": self.state.value})

    def recover(self) -> bool:
        """Return to ARMED after the external recovery workflow succeeds."""
        if self.state not in (ControllerState.ISOLATED, ControllerState.RECOVERY):
            return False
        self.state = ControllerState.RECOVERY
        self.relay_state = "ENGAGED"
        self.state = ControllerState.ARMED
        self.events.append({"event_type": "controller_recovery", "state": self.state.value})
        return True

    def mark_tampered(self) -> None:
        """Enter tampered state; real enforcement belongs to the security MCU."""
        self.state = ControllerState.TAMPERED
        self.relay_state = "ISOLATED"
        self.events.append({"event_type": "controller_state", "state": self.state.value})

    @staticmethod
    def _canonical(value: dict[str, Any]) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _tag(self, value: dict[str, Any]) -> str:
        return hmac.new(self.secret, self._canonical(value), hashlib.sha256).hexdigest()

    def issue_signal(
        self,
        *,
        event_id: str,
        source: str,
        signal_type: str,
        payload: dict[str, Any],
        issued_at: float | None = None,
    ) -> EvidenceSignal:
        """Create a signed signal for controlled simulation or adapter tests."""
        sequence = self._next_sequence.get(source, 0) + 1
        self._next_sequence[source] = sequence
        issued_at = time.time() if issued_at is None else float(issued_at)
        payload_hash = hashlib.sha256(self._canonical(payload)).hexdigest()
        unsigned = {
            "event_id": event_id,
            "source": source,
            "signal_type": signal_type,
            "sequence": sequence,
            "issued_at": issued_at,
            "payload_hash": payload_hash,
        }
        return EvidenceSignal(
            signal_id=f"sig-{source}-{sequence}",
            event_id=event_id,
            source=source,
            signal_type=signal_type,
            sequence=sequence,
            issued_at=issued_at,
            payload=dict(payload),
            payload_hash=payload_hash,
            auth_tag=self._tag(unsigned),
        )

    def verify_signal(self, signal: EvidenceSignal, *, now: float | None = None) -> tuple[bool, str]:
        """Verify authentication, payload integrity, freshness, and replay state."""
        now = time.time() if now is None else float(now)
        unsigned = {
            "event_id": signal.event_id,
            "source": signal.source,
            "signal_type": signal.signal_type,
            "sequence": signal.sequence,
            "issued_at": signal.issued_at,
            "payload_hash": signal.payload_hash,
        }
        if not hmac.compare_digest(signal.auth_tag, self._tag(unsigned)):
            return False, "AUTH_FAILED"
        actual_hash = hashlib.sha256(self._canonical(signal.payload)).hexdigest()
        if not hmac.compare_digest(signal.payload_hash, actual_hash):
            return False, "PAYLOAD_HASH_FAILED"
        if abs(now - signal.issued_at) > self.freshness_window_seconds:
            return False, "STALE"
        highest = self._highest_sequence.get(signal.source, 0)
        if signal.sequence <= highest:
            return False, "REPLAYED_OR_OUT_OF_ORDER"
        return True, "ACCEPTED"

    def submit_signal(self, signal: EvidenceSignal, *, now: float | None = None) -> dict[str, Any]:
        """Submit evidence and evaluate the two-signal containment policy."""
        valid, reason = self.verify_signal(signal, now=now)
        event = {
            "event_type": "signal_accepted" if valid else "signal_rejected",
            "signal_id": signal.signal_id,
            "source": signal.source,
            "signal_type": signal.signal_type,
            "reason": reason,
        }
        self.events.append(event)
        if not valid:
            return {"accepted": False, "reason": reason, "state": self.state.value}
        if signal.signal_id in self._signals:
            return {"accepted": False, "reason": "DUPLICATE_SIGNAL", "state": self.state.value}
        self._highest_sequence[signal.source] = signal.sequence
        self._signals[signal.signal_id] = signal
        self.state = ControllerState.ALERT_PENDING
        result = self._evaluate(event_id=signal.event_id, now=now)
        return {"accepted": True, "reason": reason, **result}

    def issue_vote(
        self,
        *,
        event_id: str,
        peer_id: str,
        decision: str = "ISOLATE",
        issued_at: float | None = None,
    ) -> PeerVote:
        sequence = self._next_sequence.get(f"peer:{peer_id}", 0) + 1
        self._next_sequence[f"peer:{peer_id}"] = sequence
        issued_at = time.time() if issued_at is None else float(issued_at)
        unsigned = {
            "event_id": event_id,
            "peer_id": peer_id,
            "decision": decision,
            "sequence": sequence,
            "issued_at": issued_at,
        }
        return PeerVote(
            vote_id=f"vote-{peer_id}-{sequence}",
            event_id=event_id,
            peer_id=peer_id,
            decision=decision,
            sequence=sequence,
            issued_at=issued_at,
            auth_tag=self._tag(unsigned),
        )

    def submit_vote(self, vote: PeerVote, *, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else float(now)
        unsigned = {
            "event_id": vote.event_id,
            "peer_id": vote.peer_id,
            "decision": vote.decision,
            "sequence": vote.sequence,
            "issued_at": vote.issued_at,
        }
        if not hmac.compare_digest(vote.auth_tag, self._tag(unsigned)):
            return {"accepted": False, "reason": "AUTH_FAILED", "state": self.state.value}
        if abs(now - vote.issued_at) > self.freshness_window_seconds:
            return {"accepted": False, "reason": "STALE", "state": self.state.value}
        highest = self._highest_sequence.get(f"peer:{vote.peer_id}", 0)
        if vote.sequence <= highest:
            return {"accepted": False, "reason": "REPLAYED_OR_OUT_OF_ORDER", "state": self.state.value}
        self._highest_sequence[f"peer:{vote.peer_id}"] = vote.sequence
        self._votes[vote.vote_id] = vote
        self.events.append({"event_type": "vote_accepted", "vote_id": vote.vote_id, "peer_id": vote.peer_id})
        return self._evaluate(event_id=vote.event_id, now=now)

    def _evaluate(self, *, event_id: str, now: float | None) -> dict[str, Any]:
        signals = [s for s in self._signals.values() if s.event_id == event_id]
        signal_types = {s.signal_type for s in signals}
        votes = [v for v in self._votes.values() if v.event_id == event_id and v.decision == "ISOLATE"]
        quorum_ok = self.quorum_required == 0 or len({v.peer_id for v in votes}) >= self.quorum_required
        signals_ok = set(self.required_signals).issubset(signal_types)
        if signals_ok and quorum_ok:
            return self._isolate(event_id=event_id, signals=signals, votes=votes, now=now)
        return {
            "decision": "PENDING",
            "state": self.state.value,
            "signals_received": sorted(signal_types),
            "signals_required": list(self.required_signals),
            "quorum_received": len({v.peer_id for v in votes}),
            "quorum_required": self.quorum_required,
        }

    def _isolate(self, *, event_id: str, signals: list[EvidenceSignal], votes: list[PeerVote], now: float | None) -> dict[str, Any]:
        self.state = ControllerState.ISOLATED
        self.relay_state = "ISOLATED"
        self.counter += 1
        created_at = time.time() if now is None else float(now)
        receipt_body = {
            "receipt_id": f"receipt-{self.counter:08d}",
            "event_id": event_id,
            "counter": self.counter,
            "controller_state": self.state.value,
            "decision": "ISOLATE",
            "evidence_ids": [s.signal_id for s in signals],
            "vote_ids": [v.vote_id for v in votes],
            "relay_requested": "ISOLATED",
            "relay_acknowledged": "ISOLATED",
            "created_at": created_at,
            "external_witness_status": "NOT_CONFIGURED",
        }
        receipt_hash = hashlib.sha256(self._canonical(receipt_body)).hexdigest()
        receipt = DecisionReceipt(
            receipt_hash=receipt_hash,
            auth_tag=self._tag({**receipt_body, "receipt_hash": receipt_hash}),
            **receipt_body,
        )
        self.receipts.append(receipt)
        self.events.append({"event_type": "containment_approved", "receipt_id": receipt.receipt_id})
        return {
            "decision": "ISOLATE",
            "state": self.state.value,
            "relay_state": self.relay_state,
            "receipt": asdict(receipt),
            "signals_received": sorted({s.signal_type for s in signals}),
            "quorum_received": len({v.peer_id for v in votes}),
            "quorum_required": self.quorum_required,
        }

    def verify_receipt(self, receipt: DecisionReceipt | dict[str, Any]) -> tuple[bool, str]:
        data = asdict(receipt) if isinstance(receipt, DecisionReceipt) else dict(receipt)
        receipt_hash = data.pop("receipt_hash")
        auth_tag = data.pop("auth_tag")
        expected_hash = hashlib.sha256(self._canonical(data)).hexdigest()
        if not hmac.compare_digest(receipt_hash, expected_hash):
            return False, "RECEIPT_HASH_FAILED"
        expected_tag = self._tag({**data, "receipt_hash": receipt_hash})
        if not hmac.compare_digest(auth_tag, expected_tag):
            return False, "RECEIPT_AUTH_FAILED"
        return True, "VALID"

    def snapshot(self) -> dict[str, Any]:
        """Return safe GUI telemetry without exposing the controller secret."""
        latest = self.receipts[-1] if self.receipts else None
        return {
            "controller_state": self.state.value,
            "relay_requested": self.relay_state,
            "relay_acknowledged": self.relay_state,
            "signals": [e for e in self.events if e["event_type"] == "signal_accepted"][-10:],
            "quorum": {
                "required": self.quorum_required,
                "received": len({v.peer_id for v in self._votes.values()}),
                "decision": "CONFIRMED" if self.state == ControllerState.ISOLATED else "PENDING",
            },
            "receipt": asdict(latest) if latest else None,
            "receipt_verification": self.verify_receipt(latest)[1] if latest else "NOT_AVAILABLE",
        }
