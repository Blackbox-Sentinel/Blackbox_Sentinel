"""M3-owned security contracts for evidence gating and containment receipts.

This module is software-only and hardware-independent. It does not switch a
relay, invalidate a hardware key, or send wire messages. M1/M2 will later bind
these contracts to the trusted controller and authenticated transport.

M3 responsibilities implemented here:
- require two fresh, authenticated, independent compromise signals;
- bind the decision to a canonical evidence digest;
- issue an externally verifiable Ed25519 containment receipt;
- maintain a software monotonic receipt counter for simulation.

The software counter and in-memory signing key are not hardware-backed. They
are deliberately explicit so the hardware-backed replacement boundary is
visible rather than being mistaken for a completed security feature.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature


RECEIPT_VERSION = 1
RECEIPT_ALGORITHM = "Ed25519"


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _safe_id(value: str, field: str) -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 120:
        raise ValueError(f"{field} must be 1–120 non-whitespace characters")
    return cleaned


@dataclass(frozen=True)
class EvidenceSignal:
    """One independently authenticated signal about an incident."""

    signal_id: str
    source_id: str
    signal_type: str
    decision: str
    authenticated: bool
    fresh: bool
    confidence: float | None = None
    details: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        _safe_id(self.signal_id, "signal_id")
        _safe_id(self.source_id, "source_id")
        _safe_id(self.signal_type, "signal_type")
        if self.decision not in {"CONFIRM", "DENY", "ABSTAIN"}:
            raise ValueError("decision must be CONFIRM, DENY, or ABSTAIN")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "source_id": self.source_id,
            "signal_type": self.signal_type,
            "decision": self.decision,
            "authenticated": self.authenticated,
            "fresh": self.fresh,
            "confidence": self.confidence,
            "details": dict(self.details or {}),
        }


@dataclass(frozen=True)
class EvidenceDecision:
    """Deterministic M3 decision before a trusted controller acts."""

    incident_id: str
    approved: bool
    reason: str
    accepted_signals: tuple[EvidenceSignal, ...]
    evidence_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "approved": self.approved,
            "reason": self.reason,
            "accepted_signals": [signal.to_dict() for signal in self.accepted_signals],
            "evidence_digest": self.evidence_digest,
        }


class TwoSignalGate:
    """Require two distinct authenticated and fresh compromise signals.

    The default policy requires distinct source IDs and distinct signal types.
    This prevents two fields copied from the same detector or the same node
    from pretending to be independent evidence.
    """

    def __init__(self, required_signals: int = 2) -> None:
        if required_signals < 2:
            raise ValueError("required_signals must be at least 2")
        self.required_signals = required_signals

    def evaluate(
        self,
        incident_id: str,
        signals: Sequence[EvidenceSignal],
    ) -> EvidenceDecision:
        incident_id = _safe_id(incident_id, "incident_id")
        valid: list[EvidenceSignal] = []
        seen_signal_ids: set[str] = set()
        seen_sources: set[str] = set()
        seen_types: set[str] = set()

        for signal in signals:
            if signal.signal_id in seen_signal_ids:
                continue
            seen_signal_ids.add(signal.signal_id)
            if signal.decision != "CONFIRM":
                continue
            if not signal.authenticated or not signal.fresh:
                continue
            if signal.source_id in seen_sources or signal.signal_type in seen_types:
                continue
            valid.append(signal)
            seen_sources.add(signal.source_id)
            seen_types.add(signal.signal_type)

        accepted = tuple(valid[: self.required_signals])
        approved = len(accepted) >= self.required_signals
        reason = (
            "independent authenticated fresh signals reached the required threshold"
            if approved
            else "insufficient independent authenticated fresh signals"
        )
        evidence = {
            "incident_id": incident_id,
            "required_signals": self.required_signals,
            "signals": [signal.to_dict() for signal in signals],
            "accepted_signal_ids": [signal.signal_id for signal in accepted],
            "approved": approved,
        }
        digest = hashlib.sha256(_canonical_json(evidence)).hexdigest()
        return EvidenceDecision(
            incident_id=incident_id,
            approved=approved,
            reason=reason,
            accepted_signals=accepted,
            evidence_digest=digest,
        )


class SoftwareMonotonicCounter:
    """Crash-safe software counter for simulation, not secure hardware."""

    def __init__(self, path: str | Path, initial: int = 0) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                value = int(self.path.read_text(encoding="utf-8").strip())
            except (OSError, ValueError) as exc:
                raise ValueError(f"Invalid monotonic counter: {self.path}") from exc
            if value < 0:
                raise ValueError("monotonic counter cannot be negative")
            self.value = value
        else:
            if initial < 0:
                raise ValueError("initial counter cannot be negative")
            self.value = int(initial)
            self._persist()

    def next(self) -> int:
        self.value += 1
        self._persist()
        return self.value

    def _persist(self) -> None:
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(f"{self.value}\n", encoding="utf-8")
        os.replace(temporary, self.path)


class Ed25519ReceiptSigner:
    """Sign and verify canonical receipt payloads.

    A private key may be generated in memory for simulation. Production M1
    integration must supply a controller-held key and must not persist it in
    this Python module or in the repository.
    """

    def __init__(self, private_key: Ed25519PrivateKey | None = None) -> None:
        self.private_key = private_key or Ed25519PrivateKey.generate()

    @classmethod
    def from_private_bytes(cls, private_bytes: bytes) -> "Ed25519ReceiptSigner":
        return cls(Ed25519PrivateKey.from_private_bytes(private_bytes))

    def public_key_bytes(self) -> bytes:
        return self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )

    def sign(self, payload: Mapping[str, Any]) -> str:
        return _b64(self.private_key.sign(_canonical_json(payload)))

    def verify(
        self,
        payload: Mapping[str, Any],
        signature: str,
        public_key: Ed25519PublicKey | bytes,
    ) -> bool:
        key = (
            Ed25519PublicKey.from_public_bytes(public_key)
            if isinstance(public_key, bytes)
            else public_key
        )
        try:
            key.verify(_unb64(signature), _canonical_json(payload))
        except (InvalidSignature, ValueError):
            return False
        return True


class ContainmentReceiptService:
    """Create and verify M3 containment receipts for the existing ledger."""

    def __init__(
        self,
        ledger: Any,
        counter: SoftwareMonotonicCounter,
        signer: Ed25519ReceiptSigner,
        controller_id: str = "software-sim-controller",
    ) -> None:
        self.ledger = ledger
        self.counter = counter
        self.signer = signer
        self.controller_id = _safe_id(controller_id, "controller_id")

    def issue(
        self,
        decision: EvidenceDecision,
        organization_id: str,
        key_epoch: int,
        quorum: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not decision.approved:
            raise ValueError("cannot issue a containment receipt for an unapproved decision")
        if key_epoch < 0:
            raise ValueError("key_epoch cannot be negative")
        organization_id = _safe_id(organization_id, "organization_id")
        event = self.ledger.add_entry(
            "containment_decision",
            {
                "organization_id": organization_id,
                "incident_id": decision.incident_id,
                "evidence_digest": decision.evidence_digest,
                "accepted_signal_ids": [
                    signal.signal_id for signal in decision.accepted_signals
                ],
                "quorum": dict(quorum),
                "controller_id": self.controller_id,
            },
        )
        sequence = self.counter.next()
        payload = {
            "receipt_version": RECEIPT_VERSION,
            "algorithm": RECEIPT_ALGORITHM,
            "receipt_sequence": sequence,
            "organization_id": organization_id,
            "controller_id": self.controller_id,
            "incident_id": decision.incident_id,
            "decision": "CONTAIN",
            "event_hash": event["hash"],
            "evidence_digest": decision.evidence_digest,
            "key_epoch": int(key_epoch),
            "quorum": dict(quorum),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        receipt = {
            "payload": payload,
            "signature": self.signer.sign(payload),
            "public_key": _b64(self.signer.public_key_bytes()),
        }
        self.ledger.add_entry(
            "containment_receipt",
            {
                "organization_id": organization_id,
                "incident_id": decision.incident_id,
                "receipt_sequence": sequence,
                "event_hash": event["hash"],
                "receipt_signature": receipt["signature"],
                "algorithm": RECEIPT_ALGORITHM,
            },
        )
        return receipt

    @staticmethod
    def verify(receipt: Mapping[str, Any]) -> bool:
        payload = receipt.get("payload")
        signature = receipt.get("signature")
        public_key = receipt.get("public_key")
        if not isinstance(payload, Mapping):
            return False
        if not isinstance(signature, str) or not isinstance(public_key, str):
            return False
        if payload.get("algorithm") != RECEIPT_ALGORITHM:
            return False
        try:
            key = Ed25519PublicKey.from_public_bytes(_unb64(public_key))
            key.verify(_unb64(signature), _canonical_json(payload))
        except (InvalidSignature, ValueError, TypeError):
            return False
        return True


__all__ = [
    "ContainmentReceiptService",
    "Ed25519ReceiptSigner",
    "EvidenceDecision",
    "EvidenceSignal",
    "SoftwareMonotonicCounter",
    "TwoSignalGate",
]
