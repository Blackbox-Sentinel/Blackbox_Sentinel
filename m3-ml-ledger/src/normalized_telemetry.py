"""Versioned, normalized M3 telemetry for the M4 dashboard.

The event intentionally contains status and verification metadata only. It does
not expose HMAC keys, private signing material, provisioning data, or raw packet
payloads. Hardware-related fields describe the software simulation boundary and
must not be interpreted as ESP32 evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from m3_contract import TELEMETRY_SCHEMA_VERSION


@dataclass
class NormalizedTelemetry:
    """Stable event shape shared by M3 and M4 during Phase-2 integration."""

    event_type: str
    timestamp: str
    organization_id: str
    node_id: str
    incident_id: str
    model: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    quorum: dict[str, Any] = field(default_factory=dict)
    receipt: dict[str, Any] = field(default_factory=dict)
    controller: dict[str, Any] = field(default_factory=dict)
    actuation: dict[str, Any] = field(default_factory=dict)
    hardware: dict[str, Any] = field(default_factory=dict)
    recovery: dict[str, Any] = field(default_factory=dict)
    schema_version: int = TELEMETRY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready event and reject accidental secret exposure."""
        payload = asdict(self)
        _assert_no_secrets(payload)
        return payload

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "NormalizedTelemetry":
        """Rehydrate an event while requiring the current schema version."""
        if int(value.get("schema_version", -1)) != TELEMETRY_SCHEMA_VERSION:
            raise ValueError("unsupported telemetry schema version")
        fields = {
            "event_type",
            "timestamp",
            "organization_id",
            "node_id",
            "incident_id",
            "model",
            "evidence",
            "quorum",
            "receipt",
            "controller",
            "actuation",
            "hardware",
            "recovery",
            "schema_version",
        }
        unknown = set(value) - fields
        if unknown:
            raise ValueError(f"unknown telemetry fields: {sorted(unknown)}")
        event = cls(
            event_type=str(value["event_type"]),
            timestamp=str(value["timestamp"]),
            organization_id=str(value["organization_id"]),
            node_id=str(value["node_id"]),
            incident_id=str(value["incident_id"]),
            model=dict(value.get("model", {})),
            evidence=dict(value.get("evidence", {})),
            quorum=dict(value.get("quorum", {})),
            receipt=dict(value.get("receipt", {})),
            controller=dict(value.get("controller", {})),
            actuation=dict(value.get("actuation", {})),
            hardware=dict(value.get("hardware", {})),
            recovery=dict(value.get("recovery", {})),
            schema_version=int(value["schema_version"]),
        )
        _assert_no_secrets(event.to_dict())
        return event


def _assert_no_secrets(value: Any, path: str = "telemetry") -> None:
    """Fail closed if a caller tries to place secret material in telemetry."""
    forbidden = {
        "key",
        "secret",
        "private_key",
        "private_key_bytes",
        "hmac_key",
        "provisioning_secret",
        "auth_key",
    }
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower()
            if normalized in forbidden or any(token in normalized for token in ("private", "secret")):
                raise ValueError(f"secret-like field is not allowed in {path}.{key}")
            _assert_no_secrets(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_no_secrets(child, f"{path}[{index}]")


__all__ = ["NormalizedTelemetry", "TELEMETRY_SCHEMA_VERSION"]
