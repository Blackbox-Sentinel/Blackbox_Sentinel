"""Simulation adapter for the M1 trusted-controller boundary.

This adapter lets M2/M3/M4 validate the decision contract without physical
hardware. It deliberately does not claim to provide real relay isolation,
hardware-backed key invalidation, tamper enforcement, or power-fail behavior.

The simulated controller:
- rejects direct unauthenticated isolate requests;
- accepts containment only when a receipt verifies and the quorum state is
  APPROVED;
- exposes a GUI-friendly status snapshot;
- keeps recovery explicit rather than silently restoring service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from m3_security_contracts import ContainmentReceiptService
from quorum_state import QuorumState


@dataclass(frozen=True)
class ControllerStatus:
    controller_id: str
    relay_state: str
    trusted_decision: bool
    receipt_verified: bool
    quorum_state: str
    recovery_required: bool
    last_incident_id: str | None
    last_rejection: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "controller_id": self.controller_id,
            "relay_state": self.relay_state,
            "trusted_decision": self.trusted_decision,
            "receipt_verified": self.receipt_verified,
            "quorum_state": self.quorum_state,
            "recovery_required": self.recovery_required,
            "last_incident_id": self.last_incident_id,
            "last_rejection": self.last_rejection,
        }


class SimTrustedController:
    """Reference implementation of the controller-side decision boundary."""

    def __init__(self, controller_id: str = "sim-controller") -> None:
        self.controller_id = controller_id
        self.relay_state = "CONNECTED"
        self.trusted_decision = False
        self.receipt_verified = False
        self.quorum_state = QuorumState.COLLECTING.value
        self.recovery_required = False
        self.last_incident_id: str | None = None
        self.last_rejection: str | None = None

    def direct_isolate(self) -> bool:
        """Reject Pi-side direct relay control in the simulation."""
        self.last_rejection = "direct_relay_control_rejected"
        return False

    def apply_containment(
        self,
        *,
        receipt: Mapping[str, Any],
        quorum_state: str,
        expected_incident_id: str,
    ) -> bool:
        self.receipt_verified = ContainmentReceiptService.verify(receipt)
        self.quorum_state = str(quorum_state)
        payload = receipt.get("payload", {})
        self.last_incident_id = payload.get("incident_id") if isinstance(payload, Mapping) else None

        if not self.receipt_verified:
            self.last_rejection = "receipt_verification_failed"
            return False
        if self.last_incident_id != expected_incident_id:
            self.last_rejection = "incident_id_mismatch"
            return False
        if self.quorum_state != QuorumState.APPROVED.value:
            self.last_rejection = "quorum_not_approved"
            return False
        if payload.get("decision") != "CONTAIN":
            self.last_rejection = "receipt_decision_not_contain"
            return False

        self.relay_state = "ISOLATED"
        self.trusted_decision = True
        self.recovery_required = False
        self.last_rejection = None
        return True

    def require_recovery(self) -> None:
        self.recovery_required = True
        self.quorum_state = QuorumState.RECOVERY_REQUIRED.value

    def authorize_recovery(self, operator_authorized: bool) -> bool:
        if not operator_authorized or not self.recovery_required:
            self.last_rejection = "recovery_authorization_required"
            return False
        self.relay_state = "CONNECTED"
        self.trusted_decision = False
        self.recovery_required = False
        self.quorum_state = QuorumState.COLLECTING.value
        self.last_rejection = None
        return True

    def status(self) -> ControllerStatus:
        return ControllerStatus(
            controller_id=self.controller_id,
            relay_state=self.relay_state,
            trusted_decision=self.trusted_decision,
            receipt_verified=self.receipt_verified,
            quorum_state=self.quorum_state,
            recovery_required=self.recovery_required,
            last_incident_id=self.last_incident_id,
            last_rejection=self.last_rejection,
        )


__all__ = ["ControllerStatus", "SimTrustedController"]
