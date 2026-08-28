"""Canonical Phase-2 M3 contract identifiers.

M2, M3, and M4 should import these identifiers instead of duplicating string
literals. The values describe the software integration contract and do not
claim that the physical M1 controller has completed validation.
"""

from __future__ import annotations


CONTRACT_ID = "blackbox-sentinel-phase2-v1"
TRANSPORT_AUTH_ALGORITHM = "HMAC-SHA256"
RECEIPT_SIGNATURE_ALGORITHM = "Ed25519"
TELEMETRY_SCHEMA_VERSION = 1
REQUIRED_INDEPENDENT_SIGNALS = 2
QUORUM_NOT_CONFIGURED = "NOT_CONFIGURED"

MESSAGE_TYPES = frozenset(
    {
        "ML_EVIDENCE",
        "PEER_EVIDENCE",
        "EVIDENCE_SIGNAL",
        "QUORUM_VOTE",
        "CONTAINMENT_RECEIPT",
        "CONTROLLER_ACK",
        "RECOVERY_STATE",
    }
)


__all__ = [
    "CONTRACT_ID",
    "MESSAGE_TYPES",
    "QUORUM_NOT_CONFIGURED",
    "RECEIPT_SIGNATURE_ALGORITHM",
    "REQUIRED_INDEPENDENT_SIGNALS",
    "TELEMETRY_SCHEMA_VERSION",
    "TRANSPORT_AUTH_ALGORITHM",
]
