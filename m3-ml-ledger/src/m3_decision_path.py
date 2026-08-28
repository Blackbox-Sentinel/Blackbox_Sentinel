"""M3 Phase-2 software decision path.

This adapter composes the existing M3 contracts without changing the 45-feature
scorer interface. A scorer result is treated as evidence, never as direct relay
authority. Containment requires independent authenticated/fresh signals, quorum
approval when quorum is configured, a signed receipt, and trusted-controller
acceptance. The controller in this module is explicitly a software simulation.
"""

from __future__ import annotations

import hashlib
import hmac
import time

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from authenticated_envelope import AuthenticatedEnvelope, ReplayProtector
from ledger import HashChainLedger
from m3_contract import (
    MESSAGE_TYPES,
    QUORUM_NOT_CONFIGURED,
    REQUIRED_INDEPENDENT_SIGNALS,
)
from m3_security_contracts import (
    ContainmentReceiptService,
    Ed25519ReceiptSigner,
    EvidenceDecision,
    EvidenceSignal,
    SoftwareMonotonicCounter,
    TwoSignalGate,
)
from normalized_telemetry import NormalizedTelemetry
from quorum_state import QuorumState, QuorumStateMachine, QuorumVote
from trusted_controller_sim import ControllerStatus, SimTrustedController


NOT_CONFIGURED = QUORUM_NOT_CONFIGURED
DEFAULT_KEYS_DIR = Path(__file__).resolve().parents[1] / "data" / "keys"


def _load_node_master_key(sender_id: str, keys_dir: Path) -> bytes:
    """Load a provisioned sender key; never create keys during verification."""
    if not sender_id or Path(sender_id).name != sender_id:
        raise ValueError("invalid sender_id for key lookup")
    key_path = keys_dir / f"{sender_id}.key"
    try:
        master_key = key_path.read_bytes()
    except FileNotFoundError as exc:
        raise ValueError(f"no provisioned key for sender: {sender_id}") from exc
    if len(master_key) != 32:
        raise ValueError("provisioned node key must be exactly 32 bytes")
    return master_key


def _derive_node_epoch_key(master_key: bytes, key_epoch: int) -> bytes:
    if not isinstance(key_epoch, int) or isinstance(key_epoch, bool) or key_epoch < 0:
        raise ValueError("key_epoch must be a non-negative integer")
    return hmac.new(
        master_key,
        str(key_epoch).encode("utf-8"),
        hashlib.sha256,
    ).digest()


@dataclass(frozen=True)

class DecisionPathResult:
    """Machine-readable result returned to M4 and integration tests."""

    status: str
    incident_id: str
    reason: str
    telemetry: dict[str, Any]
    decision: dict[str, Any]
    receipt: dict[str, Any] | None
    controller: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "incident_id": self.incident_id,
            "reason": self.reason,
            "telemetry": self.telemetry,
            "decision": self.decision,
            "receipt": self.receipt,
            "controller": self.controller,
        }


class M3DecisionPath:
    """Connect M3 scoring evidence to the software controller boundary."""

    def __init__(
        self,
        *,
        ledger: HashChainLedger,
        node_id: str,
        organization_id: str,
        counter_path: str | Path,
        controller_id: str = "sim-controller",
        key_epoch: int = 1,
        expected_voters: Sequence[str] | None = None,
        required_confirmations: int | None = None,
        quorum_deadline_seconds: float = 30.0,
        signer: Ed25519ReceiptSigner | None = None,
        replay_protector: ReplayProtector | None = None,
        keys_dir: str | Path | None = None,
    ) -> None:

        if not node_id.strip():
            raise ValueError("node_id must not be empty")
        if not organization_id.strip():
            raise ValueError("organization_id must not be empty")
        if key_epoch < 0:
            raise ValueError("key_epoch cannot be negative")
        if quorum_deadline_seconds <= 0:
            raise ValueError("quorum_deadline_seconds must be positive")
        if (expected_voters is None) != (required_confirmations is None):
            raise ValueError(
                "expected_voters and required_confirmations must be provided together"
            )
        if expected_voters is not None and not expected_voters:
            raise ValueError("expected_voters cannot be empty when quorum is configured")

        self.ledger = ledger
        self.node_id = node_id.strip()
        self.organization_id = organization_id.strip()
        self.key_epoch = int(key_epoch)
        self.controller = SimTrustedController(controller_id)
        self.gate = TwoSignalGate(required_signals=REQUIRED_INDEPENDENT_SIGNALS)
        self.quorum = QuorumStateMachine()
        self.expected_voters = tuple(expected_voters or ())
        self.required_confirmations = required_confirmations
        self.quorum_deadline_seconds = float(quorum_deadline_seconds)
        self.signer = signer or Ed25519ReceiptSigner()
        self.counter = SoftwareMonotonicCounter(counter_path)
        self.receipts = ContainmentReceiptService(
            ledger=ledger,
            counter=self.counter,
            signer=self.signer,
            controller_id=controller_id,
        )
        self.replay_protector = replay_protector or ReplayProtector()
        self.keys_dir = Path(keys_dir) if keys_dir is not None else None
        self._incident_sequence = 0

    def _verification_key(self, envelope: AuthenticatedEnvelope, supplied_key: bytes | None) -> bytes:
        """Resolve a sender/epoch key without trusting a caller-supplied key."""
        if self.keys_dir is None:
            if supplied_key is None:
                raise ValueError("verification key is required when keys_dir is unset")
            return supplied_key
        master_key = _load_node_master_key(envelope.sender_id, self.keys_dir)
        return _derive_node_epoch_key(master_key, envelope.key_epoch)

    @property

    def quorum_configured(self) -> bool:
        return self.required_confirmations is not None

    def accept_authenticated_envelope(
        self,
        envelope: AuthenticatedEnvelope,
        key: bytes | None = None,
        *,
        now: float | None = None,
    ) -> bool:

        """Verify one M2 envelope at the M3 boundary.

        M2 may perform this check at the transport boundary as well. Keeping the
        method here lets the software vertical slice verify the same contract
        before M3 consumes an evidence or vote payload.
        """
        return self.replay_protector.accept(
            envelope, self._verification_key(envelope, key), now=now
        )

    def evidence_signal_from_envelope(
        self,
        envelope: AuthenticatedEnvelope,
        key: bytes | None = None,
        *,
        now: float | None = None,
    ) -> EvidenceSignal:

        """Verify and decode one authenticated evidence envelope from M2."""
        if envelope.message_type not in {"ML_EVIDENCE", "PEER_EVIDENCE", "EVIDENCE_SIGNAL"}:

            raise ValueError("envelope is not an evidence message")
        if envelope.message_type not in MESSAGE_TYPES:
            raise ValueError("unsupported message type")
        if not self.accept_authenticated_envelope(envelope, key, now=now):
            raise ValueError("authenticated evidence envelope rejected")
        payload = dict(envelope.payload)
        signal_id = payload.get("signal_id", f"{envelope.sender_id}:{envelope.sequence}")
        signal_type = payload.get("signal_type")
        decision = payload.get("decision")
        if not isinstance(signal_type, str) or not isinstance(decision, str):
            raise ValueError("evidence payload requires signal_type and decision")
        details = payload.get("details", {})
        if not isinstance(details, Mapping):
            raise ValueError("evidence details must be a mapping")
        return EvidenceSignal(
            signal_id=str(signal_id),
            # The authenticated envelope sender is authoritative. Do not trust
            # a source_id copied into the payload for independence evaluation.
            source_id=envelope.sender_id,
            signal_type=signal_type,
            decision=decision,
            authenticated=True,
            fresh=True,
            confidence=(
                float(payload["confidence"])
                if payload.get("confidence") is not None
                else None
            ),
            details=details,
        )

    def quorum_vote_from_envelope(
        self,
        envelope: AuthenticatedEnvelope,
        key: bytes | None = None,
        *,
        now: float | None = None,
    ) -> QuorumVote:

        """Verify and decode one authenticated quorum vote from M2."""
        if envelope.message_type != "QUORUM_VOTE":
            raise ValueError("envelope is not a quorum-vote message")
        if not self.accept_authenticated_envelope(envelope, key, now=now):
            raise ValueError("authenticated quorum envelope rejected")
        payload = dict(envelope.payload)
        for field in ("incident_id", "decision", "evidence_digest"):
            if field not in payload:
                raise ValueError(f"quorum payload requires {field}")
        received_at = time.time() if now is None else float(now)
        return QuorumVote(
            incident_id=str(payload["incident_id"]),
            voter_id=envelope.sender_id,
            decision=str(payload["decision"]),
            evidence_digest=str(payload["evidence_digest"]),
            sequence=envelope.sequence,
            authenticated=True,
            fresh=True,
            received_at=received_at,
        )

    def submit_authenticated(
        self,
        *,
        model_result: Mapping[str, Any],
        evidence_envelopes: Sequence[tuple[AuthenticatedEnvelope, bytes]],
        incident_id: str,
        quorum_envelopes: Sequence[tuple[AuthenticatedEnvelope, bytes]] = (),
        now: float | None = None,
    ) -> DecisionPathResult:
        """Decode M2 envelopes and submit one complete M3 policy decision."""
        signals = [
            self.evidence_signal_from_envelope(envelope, key, now=now)
            for envelope, key in evidence_envelopes
        ]
        votes = [
            self.quorum_vote_from_envelope(envelope, key, now=now)
            for envelope, key in quorum_envelopes
        ]
        return self.submit(
            model_result=model_result,
            signals=signals,
            incident_id=incident_id,
            quorum_votes=votes,
            now=now,
        )

    def submit(
        self,
        *,
        model_result: Mapping[str, Any],
        signals: Sequence[EvidenceSignal] | None = None,
        incident_id: str | None = None,
        quorum_votes: Sequence[QuorumVote] | None = None,
        now: float | None = None,
        key_epoch: int | None = None,
    ) -> DecisionPathResult:
        """Evaluate a scored window and return normalized M4 telemetry.

        ``signals`` should contain the M3 signal plus an independently sourced
        signal from M2, a peer, or another approved detector. If omitted, one
        M3 signal is synthesized from the model result, which can never satisfy
        the two-signal gate by itself.
        """
        current_time = time.time() if now is None else float(now)
        incident = incident_id or self._next_incident_id()
        signal_list = tuple(signals or (self._model_signal(model_result),))
        decision = self.gate.evaluate(incident, signal_list)
        quorum_snapshot: dict[str, Any] = {"state": NOT_CONFIGURED}
        receipt: dict[str, Any] | None = None
        controller_accepted = False
        status = "PENDING_EVIDENCE"
        reason = decision.reason

        if not bool(model_result.get("is_anomaly", False)):
            status = "BENIGN"
            reason = "model result did not request an alert"
        elif decision.approved:
            if self.quorum_configured:
                quorum_state = self._evaluate_quorum(
                    decision,
                    quorum_votes or (),
                    current_time,
                )
                quorum_snapshot = self.quorum.snapshot(incident)
                policy_approved = quorum_state == QuorumState.APPROVED
            else:
                # An explicitly unconfigured quorum is represented honestly in
                # telemetry. The independent two-signal policy remains the
                # approval gate for this software-only deployment.
                quorum_state = None
                policy_approved = True

            if not policy_approved:
                status = "PENDING_QUORUM"
                reason = f"quorum state is {quorum_state.value}"
                self.ledger.add_entry(
                    "containment_rejected",
                    {
                        "organization_id": self.organization_id,
                        "incident_id": incident,
                        "reason": reason,
                        "evidence_digest": decision.evidence_digest,
                        "quorum": quorum_snapshot,
                    },
                )
            else:
                receipt = self.receipts.issue(
                    decision=decision,
                    organization_id=self.organization_id,
                    key_epoch=self.key_epoch if key_epoch is None else int(key_epoch),
                    quorum=quorum_snapshot,
                )
                controller_accepted = self.controller.apply_containment(
                    receipt=receipt,
                    quorum_state=QuorumState.APPROVED.value,
                    expected_incident_id=incident,
                )
                if controller_accepted:
                    status = "CONTAINMENT_ACCEPTED"
                    reason = "signed receipt verified and simulated controller accepted containment"
                    self.ledger.add_entry(
                        "controller_containment_accepted",
                        {
                            "organization_id": self.organization_id,
                            "incident_id": incident,
                            "receipt_sequence": receipt["payload"]["receipt_sequence"],
                            "controller_id": self.controller.controller_id,
                            "hardware_enforcement": False,
                        },
                    )
                else:
                    status = "CONTROLLER_REJECTED"
                    reason = self.controller.status().last_rejection or "controller rejected receipt"
                    self.ledger.add_entry(
                        "controller_containment_rejected",
                        {
                            "organization_id": self.organization_id,
                            "incident_id": incident,
                            "receipt_sequence": receipt["payload"]["receipt_sequence"],
                            "controller_id": self.controller.controller_id,
                            "reason": reason,
                            "hardware_enforcement": False,
                        },
                    )
        else:
            self.ledger.add_entry(
                "evidence_rejected",
                {
                    "organization_id": self.organization_id,
                    "incident_id": incident,
                    "reason": decision.reason,
                    "evidence_digest": decision.evidence_digest,
                    "signal_count": len(signal_list),
                },
            )

        controller_status = self.controller.status()
        telemetry = self._telemetry(
            model_result=model_result,
            incident_id=incident,
            signal_list=signal_list,
            decision=decision,
            quorum_snapshot=quorum_snapshot,
            receipt=receipt,
            controller_status=controller_status,
            status=status,
            now=current_time,
            controller_accepted=controller_accepted,
        )
        return DecisionPathResult(
            status=status,
            incident_id=incident,
            reason=reason,
            telemetry=telemetry,
            decision=decision.to_dict(),
            receipt=receipt,
            controller=controller_status.to_dict(),
        )

    def mark_recovery_required(self, incident_id: str) -> dict[str, Any]:
        """Expose explicit recovery state for M4 without restoring the relay."""
        if self.quorum_configured and incident_id in self.quorum.incidents:
            self.quorum.mark_recovery_required(incident_id)
        self.controller.require_recovery()
        status = self.controller.status()
        self.ledger.add_entry(
            "recovery_required",
            {
                "organization_id": self.organization_id,
                "incident_id": incident_id,
                "controller_id": status.controller_id,
                "relay_state": status.relay_state,
                "recovery_required": True,
            },
        )
        return status.to_dict()

    def authorize_recovery(self, operator_authorized: bool) -> dict[str, Any]:
        """Restore only the software controller simulation after authorization."""
        accepted = self.controller.authorize_recovery(operator_authorized)
        status = self.controller.status()
        self.ledger.add_entry(
            "recovery_authorization",
            {
                "organization_id": self.organization_id,
                "controller_id": status.controller_id,
                "authorized": bool(operator_authorized),
                "accepted": accepted,
                "relay_state": status.relay_state,
            },
        )
        return status.to_dict()

    def _evaluate_quorum(
        self,
        decision: EvidenceDecision,
        votes: Sequence[QuorumVote],
        now: float,
    ) -> QuorumState:
        self.quorum.start(
            incident_id=decision.incident_id,
            evidence_digest=decision.evidence_digest,
            expected_voters=self.expected_voters,
            required_confirmations=int(self.required_confirmations),
            started_at=now,
            deadline_seconds=self.quorum_deadline_seconds,
        )
        state = QuorumState.COLLECTING
        for vote in votes:
            state = self.quorum.add_vote(vote)
            if state != QuorumState.COLLECTING:
                break
        if state == QuorumState.COLLECTING and now >= self.quorum.snapshot(decision.incident_id)["deadline_at"]:
            state = self.quorum.advance_time(decision.incident_id, now)
        return state

    def _telemetry(
        self,
        *,
        model_result: Mapping[str, Any],
        incident_id: str,
        signal_list: Sequence[EvidenceSignal],
        decision: EvidenceDecision,
        quorum_snapshot: Mapping[str, Any],
        receipt: Mapping[str, Any] | None,
        controller_status: ControllerStatus,
        status: str,
        now: float,
        controller_accepted: bool,
    ) -> dict[str, Any]:
        signal_types = {signal.signal_type for signal in signal_list}
        source_ids = {signal.source_id for signal in signal_list}
        receipt_payload = receipt.get("payload", {}) if receipt else {}
        event = NormalizedTelemetry(
            event_type=status,
            timestamp=datetime.fromtimestamp(now, timezone.utc).isoformat(),
            organization_id=self.organization_id,
            node_id=self.node_id,
            incident_id=incident_id,
            model={
                key: model_result.get(key)
                for key in (
                    "state",
                    "score",
                    "probability_attack",
                    "threshold",
                    "is_anomaly",
                    "global_prediction",
                    "local_prediction",
                    "local_detection_enabled",
                    "profile_ready",
                    "profile_samples",
                    "feature_count",
                    "timestamp",
                )
                if key in model_result
            },
            evidence={
                "digest": decision.evidence_digest,
                "signal_count": len(signal_list),
                "source_ids": sorted(source_ids),
                "signal_types": sorted(signal_types),
                "independent": len(source_ids) == len(signal_list)
                and len(signal_types) == len(signal_list),
                "signals": [signal.to_dict() for signal in signal_list],
                "approved": decision.approved,
            },
            quorum=dict(quorum_snapshot),
            receipt={
                "issued": receipt is not None,
                "receipt_id": receipt_payload.get("event_hash") if receipt else None,
                "receipt_sequence": receipt_payload.get("receipt_sequence") if receipt else None,
                "signature_verified": bool(receipt and ContainmentReceiptService.verify(receipt)),
                "ledger_bound": bool(receipt and receipt_payload.get("event_hash")),
                "algorithm": receipt_payload.get("algorithm") if receipt else None,
            },
            controller=controller_status.to_dict(),
            actuation={
                "relay_requested": receipt is not None,
                "relay_acknowledged": controller_accepted,
                "relay_verified": False,
                "verification_scope": "software-controller-only",
            },
            hardware={
                "enforcement_mode": "software-simulation",
                "physical_controller_validated": False,
                "relay_hardware_verified": False,
                "tamper_state": "UNKNOWN",
                "key_state": "NOT_EXPOSED",
                "primary_power_state": "UNKNOWN",
                "hold_up_power_state": "UNKNOWN",
            },
            recovery={
                "required": controller_status.recovery_required,
                "status": (
                    "RECOVERY_REQUIRED"
                    if controller_status.recovery_required
                    else "NOT_REQUIRED"
                ),
            },
        )
        return event.to_dict()

    def _model_signal(self, model_result: Mapping[str, Any]) -> EvidenceSignal:
        prediction = str(model_result.get("global_prediction", "BENIGN"))
        decision = "CONFIRM" if prediction == "ATTACK" or model_result.get("is_anomaly") else "DENY"
        digest_source = repr(sorted((str(key), repr(value)) for key, value in model_result.items()))
        signal_id = "ml-" + hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:16]
        return EvidenceSignal(
            signal_id=signal_id,
            source_id=self.node_id,
            signal_type="ml-v3",
            decision=decision,
            authenticated=True,
            fresh=True,
            confidence=float(model_result.get("probability_attack", 0.0)),
            details={
                "global_prediction": prediction,
                "organization_id": self.organization_id,
                "feature_count": model_result.get("feature_count"),
            },
        )

    def _next_incident_id(self) -> str:
        self._incident_sequence += 1
        return f"{self.node_id}:{self._incident_sequence}"


__all__ = ["DecisionPathResult", "M3DecisionPath", "NOT_CONFIGURED"]
