"""Normalized software telemetry contract for the BlackBox Sentinel Phase 2 slice.

M2/M3 producers may use different internal models, but the M4 dashboard consumes
only this stable, JSON-serializable object. The contract is simulation-only and
does not claim physical ESP32 enforcement.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = 1


class EventStatus(StrEnum):
    NORMAL = "normal"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REPLAY = "replay"
    STALE = "stale"
    CONFLICT = "conflict"
    RECEIPT = "receipt"
    RECOVERY = "recovery"


@dataclass
class NormalizedTelemetry:
    """The only object the M4 dashboard needs from the Phase 2 pipeline."""

    event_id: str
    event_type: str
    status: str = EventStatus.NORMAL.value
    timestamp: str = ""
    source: str = "phase2-sim"
    transport_sender: str | None = None
    transport_sequence: int | None = None
    transport_auth: str = "NOT_VERIFIED"
    freshness_status: str = "NOT_CHECKED"
    controller_state: str = "ARMED"
    link_state: str = "HEALTHY"
    incident_id: str | None = None
    packet_count: int = 0
    alert_count: int = 0
    signals: list[dict[str, Any]] = field(default_factory=list)
    quorum_state: str = "NOT_CONFIGURED"
    quorum_required: int | None = None
    quorum_received: int = 0
    quorum_votes: list[dict[str, Any]] = field(default_factory=list)
    decision: str = "WAITING"
    relay_requested: str = "NONE"
    relay_acknowledged: bool = False
    relay_verified: bool = False
    relay_state: str = "CONNECTED"
    tamper_state: str = "SECURE"
    key_state: str = "VALID"
    power_state: str = "PRIMARY"
    receipt_status: str = "NOT_AVAILABLE"
    receipt_id: str | None = None
    receipt_sequence: int | None = None
    rejection_reason: str | None = None
    recovery_state: str = "NOT_REQUIRED"
    sms_status: str = "NOT_SENT"
    evidence_digest: str | None = None
    model_profile: str | None = None
    notes: str = ""
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        self.status = str(self.status).lower()
        if self.status not in {item.value for item in EventStatus}:
            raise ValueError(f"unsupported telemetry status: {self.status}")
        if self.packet_count < 0 or self.alert_count < 0:
            raise ValueError("telemetry counters cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=True)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "NormalizedTelemetry":
        """Parse a producer mapping while ignoring future unknown fields."""
        # Handle the real M2-M3 schema mapping to NormalizedTelemetry
        # The real schema uses nested objects like 'model', 'controller', 'evidence', etc.
        
        # 1. Start with the raw mapping if it already matches (backwards compatibility)
        fields = cls.__dataclass_fields__
        data = {key: value[key] for key in fields if key in value}
        
        # 2. Map real M2-M3 nested fields to normalized flat fields
        if "incident_id" in value and "event_id" not in data:
            data["event_id"] = value["incident_id"]
        if "event_type" in value and "event_type" not in data:
            data["event_type"] = value["event_type"]
            
        # Map model results
        if "model" in value:
            m = value["model"]
            data["packet_count"] = m.get("profile_samples", 0)
            data["alert_count"] = 1 if m.get("is_anomaly") else 0
            data["model_profile"] = m.get("state", "unknown")
            data["decision"] = "CONTAIN" if m.get("is_anomaly") else "WAITING"
            
        # Map controller state
        if "controller" in value:
            c = value["controller"]
            data["controller_state"] = c.get("relay_state", "ARMED")
            data["relay_state"] = c.get("relay_state", "CONNECTED")
            data["recovery_state"] = "REQUIRED" if c.get("recovery_required") else "NOT_REQUIRED"
            
        # Map evidence and signals
        if "evidence" in value:
            e = value["evidence"]
            data["signals"] = e.get("signals", [])
            data["evidence_digest"] = e.get("digest")
            
        # Map quorum
        if "quorum" in value:
            q = value["quorum"]
            data["quorum_state"] = q.get("state", "NOT_CONFIGURED")
            
        # Map receipt
        if "receipt" in value:
            r = value["receipt"]
            data["receipt_status"] = "VALID" if r.get("signature_verified") else "NOT_AVAILABLE"
            data["receipt_id"] = r.get("receipt_id")
            data["receipt_sequence"] = r.get("receipt_sequence")
            
        # Map hardware
        if "hardware" in value:
            h = value["hardware"]
            data["tamper_state"] = h.get("tamper_state", "SECURE")
            data["power_state"] = h.get("primary_power_state", "PRIMARY")
            data["key_state"] = "VALID" if h.get("key_state") != "INVALIDATED" else "INVALIDATED"
            
        # Map transport
        if "transport_auth" not in data:
            # Check if all signals are authenticated
            signals = data.get("signals", [])
            if signals:
                data["transport_auth"] = "VERIFIED" if all(s.get("authenticated") for s in signals) else "FAILED"
            else:
                data["transport_auth"] = "NOT_VERIFIED"
                
        if "freshness_status" not in data:
            signals = data.get("signals", [])
            if signals:
                data["freshness_status"] = "FRESH" if all(s.get("fresh") for s in signals) else "STALE"
            else:
                data["freshness_status"] = "NOT_CHECKED"

        # Final cleanup for mandatory fields
        if "event_id" not in data:
            data["event_id"] = f"evt-{datetime.now().timestamp()}"
        if "event_type" not in data:
            data["event_type"] = "unknown"

        return cls(**data)

    @classmethod
    def from_json(cls, value: str) -> "NormalizedTelemetry":
        parsed = json.loads(value)
        if not isinstance(parsed, Mapping):
            raise ValueError("telemetry JSON must contain an object")
        return cls.from_mapping(parsed)


class JsonlTelemetryWriter:
    """Append normalized events for a local M2/M3-to-M4 software transport."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def emit(self, telemetry: NormalizedTelemetry) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(telemetry.to_json() + "\n")
            handle.flush()


class JsonlTelemetryReader:
    """Incremental reader used by the M4 GUI and CLI validation tools."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.offset = 0

    def read_new(self) -> list[NormalizedTelemetry]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            handle.seek(self.offset)
            lines = handle.readlines()
            self.offset = handle.tell()
        events: list[NormalizedTelemetry] = []
        for line in lines:
            if line.strip():
                events.append(NormalizedTelemetry.from_json(line))
        return events


__all__ = [
    "EventStatus",
    "JsonlTelemetryReader",
    "JsonlTelemetryWriter",
    "NormalizedTelemetry",
    "SCHEMA_VERSION",
]


def write_events(path: str | Path, events: Iterable[NormalizedTelemetry]) -> None:
    writer = JsonlTelemetryWriter(path)
    for event in events:
        writer.emit(event)
