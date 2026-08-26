"""Shared authenticated message envelope for BlackBox Sentinel.

This is the software reference contract for B1. It can be used by the
simulation and host-side code before the M1 firmware transport is available.
M2 owns the eventual wire transport; M3 owns the fields required to bind ML
evidence, incidents, votes, and receipts to authenticated messages.

The envelope uses HMAC-SHA256 for fast transport authentication. It provides:
- canonical serialization;
- sender/recipient/message-type binding;
- per-sender monotonic sequence numbers;
- timestamp freshness checks;
- key ID and key epoch metadata;
- replay rejection with constant-time MAC comparison.

This module does not persist production secrets and does not claim hardware-
backed key protection. Production key storage remains an M1/controller task.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping

from m3_contract import TRANSPORT_AUTH_ALGORITHM


ENVELOPE_VERSION = 1
AUTH_ALGORITHM = TRANSPORT_AUTH_ALGORITHM


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _safe_text(value: str, field: str, max_length: int = 120) -> str:
    value = value.strip()
    if not value or len(value) > max_length:
        raise ValueError(f"{field} must be 1–{max_length} non-whitespace characters")
    return value


def _validate_key(key: bytes) -> bytes:
    if not isinstance(key, bytes) or len(key) < 16:
        raise ValueError("HMAC key must be at least 16 bytes")
    return key


@dataclass(frozen=True)
class AuthenticatedEnvelope:
    """A signed-by-MAC protocol message with freshness metadata."""

    sender_id: str
    recipient: str
    message_type: str
    sequence: int
    timestamp: float
    payload: Mapping[str, Any]
    key_id: str
    key_epoch: int
    auth_tag: str
    version: int = ENVELOPE_VERSION
    algorithm: str = AUTH_ALGORITHM

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "algorithm": self.algorithm,
            "sender_id": self.sender_id,
            "recipient": self.recipient,
            "message_type": self.message_type,
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
            "key_id": self.key_id,
            "key_epoch": self.key_epoch,
        }

    def to_dict(self) -> dict[str, Any]:
        result = self.unsigned_dict()
        result["auth_tag"] = self.auth_tag
        return result

    @classmethod
    def create(
        cls,
        *,
        sender_id: str,
        recipient: str,
        message_type: str,
        sequence: int,
        payload: Mapping[str, Any],
        key: bytes,
        key_id: str,
        key_epoch: int,
        timestamp: float | None = None,
    ) -> "AuthenticatedEnvelope":
        sender_id = _safe_text(sender_id, "sender_id")
        recipient = _safe_text(recipient, "recipient")
        message_type = _safe_text(message_type, "message_type")
        key_id = _safe_text(key_id, "key_id")
        _validate_key(key)
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            raise ValueError("sequence must be a positive integer")
        if not isinstance(key_epoch, int) or isinstance(key_epoch, bool) or key_epoch < 0:
            raise ValueError("key_epoch must be a non-negative integer")
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a mapping")
        timestamp = time.time() if timestamp is None else float(timestamp)
        if timestamp <= 0:
            raise ValueError("timestamp must be positive")
        unsigned = {
            "version": ENVELOPE_VERSION,
            "algorithm": AUTH_ALGORITHM,
            "sender_id": sender_id,
            "recipient": recipient,
            "message_type": message_type,
            "sequence": sequence,
            "timestamp": timestamp,
            "payload": dict(payload),
            "key_id": key_id,
            "key_epoch": key_epoch,
        }
        tag = hmac.new(key, _canonical_json(unsigned), hashlib.sha256).hexdigest()
        return cls(auth_tag=tag, **unsigned)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AuthenticatedEnvelope":
        required = {
            "sender_id",
            "recipient",
            "message_type",
            "sequence",
            "timestamp",
            "payload",
            "key_id",
            "key_epoch",
            "auth_tag",
        }
        missing = required.difference(value)
        if missing:
            raise ValueError(f"envelope missing fields: {sorted(missing)}")
        envelope = cls(
            sender_id=_safe_text(str(value["sender_id"]), "sender_id"),
            recipient=_safe_text(str(value["recipient"]), "recipient"),
            message_type=_safe_text(str(value["message_type"]), "message_type"),
            sequence=value["sequence"],
            timestamp=float(value["timestamp"]),
            payload=value["payload"],
            key_id=_safe_text(str(value["key_id"]), "key_id"),
            key_epoch=value["key_epoch"],
            auth_tag=str(value["auth_tag"]),
            version=int(value.get("version", ENVELOPE_VERSION)),
            algorithm=str(value.get("algorithm", AUTH_ALGORITHM)),
        )
        if not isinstance(envelope.sequence, int) or isinstance(envelope.sequence, bool):
            raise ValueError("sequence must be an integer")
        if not isinstance(envelope.key_epoch, int) or isinstance(envelope.key_epoch, bool):
            raise ValueError("key_epoch must be an integer")
        if not isinstance(envelope.payload, Mapping):
            raise ValueError("payload must be a mapping")
        if len(envelope.auth_tag) != 64:
            raise ValueError("auth_tag must be a SHA-256 hex digest")
        return envelope

    def verify_mac(self, key: bytes) -> bool:
        if self.version != ENVELOPE_VERSION or self.algorithm != AUTH_ALGORITHM:
            return False
        try:
            _validate_key(key)
            expected = hmac.new(
                key,
                _canonical_json(self.unsigned_dict()),
                hashlib.sha256,
            ).hexdigest()
        except (TypeError, ValueError, TypeError):
            return False
        return hmac.compare_digest(expected, self.auth_tag)


class ReplayProtector:
    """Verify MAC, freshness, and strict per-sender sequence monotonicity."""

    def __init__(self, max_age_seconds: float = 30.0, future_skew_seconds: float = 5.0):
        if max_age_seconds <= 0 or future_skew_seconds < 0:
            raise ValueError("invalid freshness window")
        self.max_age_seconds = float(max_age_seconds)
        self.future_skew_seconds = float(future_skew_seconds)
        self._last_sequence: dict[tuple[str, int], int] = {}

    def accept(
        self,
        envelope: AuthenticatedEnvelope,
        key: bytes,
        *,
        now: float | None = None,
    ) -> bool:
        if not envelope.verify_mac(key):
            return False
        now = time.time() if now is None else float(now)
        age = now - envelope.timestamp
        if age > self.max_age_seconds or age < -self.future_skew_seconds:
            return False
        identity = (envelope.sender_id, envelope.key_epoch)
        previous = self._last_sequence.get(identity, 0)
        if envelope.sequence <= previous:
            return False
        self._last_sequence[identity] = envelope.sequence
        return True

    def last_sequence(self, sender_id: str, key_epoch: int) -> int:
        return self._last_sequence.get((sender_id, key_epoch), 0)

    def reset_sender(self, sender_id: str, key_epoch: int) -> None:
        self._last_sequence.pop((sender_id, key_epoch), None)


@dataclass
class SequenceAllocator:
    """In-process sequence allocator; persistent/controller storage is external."""

    next_value: int = 1

    def next(self) -> int:
        if self.next_value < 1:
            raise ValueError("next_value must be positive")
        value = self.next_value
        self.next_value += 1
        return value


__all__ = [
    "AuthenticatedEnvelope",
    "ReplayProtector",
    "SequenceAllocator",
]
