"""Hardware-independent quorum state machine for BlackBox Sentinel.

This is the software reference implementation for B3. M2 owns transporting
and authenticating the vote envelopes. M1 owns enforcing the final physical
containment decision. M3 owns binding ML evidence and the final quorum state
to a deterministic digest and ledger/receipt record.

Safe defaults:
- votes must be authenticated and fresh before admission;
- one voter gets one vote per incident;
- votes from unknown voters are rejected;
- mixed CONFIRM/DENY votes become CONFLICT instead of silently approving;
- an incomplete vote set becomes TIMEOUT, never approval;
- only a clean N-of-M CONFIRM result becomes APPROVED.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping


class QuorumState(str, Enum):
    COLLECTING = "COLLECTING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    CONFLICT = "CONFLICT"
    TIMEOUT = "TIMEOUT"
    RECOVERY_REQUIRED = "RECOVERY_REQUIRED"


class VoteDecision(str, Enum):
    CONFIRM = "CONFIRM"
    DENY = "DENY"
    ABSTAIN = "ABSTAIN"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _safe_id(value: str, field: str) -> str:
    value = value.strip()
    if not value or len(value) > 120:
        raise ValueError(f"{field} must be 1–120 non-whitespace characters")
    return value


@dataclass(frozen=True)
class QuorumVote:
    incident_id: str
    voter_id: str
    decision: VoteDecision | str
    evidence_digest: str
    sequence: int
    authenticated: bool
    fresh: bool
    received_at: float

    def __post_init__(self) -> None:
        _safe_id(self.incident_id, "incident_id")
        _safe_id(self.voter_id, "voter_id")
        if not isinstance(self.decision, VoteDecision):
            object.__setattr__(self, "decision", VoteDecision(self.decision))
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 1:
            raise ValueError("sequence must be a positive integer")
        if not self.evidence_digest or len(self.evidence_digest) != 64:
            raise ValueError("evidence_digest must be a SHA-256 hex digest")
        if self.received_at <= 0:
            raise ValueError("received_at must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "voter_id": self.voter_id,
            "decision": self.decision.value,
            "evidence_digest": self.evidence_digest,
            "sequence": self.sequence,
            "authenticated": self.authenticated,
            "fresh": self.fresh,
            "received_at": self.received_at,
        }


@dataclass
class QuorumIncident:
    incident_id: str
    evidence_digest: str
    required_confirmations: int
    expected_voters: frozenset[str]
    started_at: float
    deadline_at: float
    state: QuorumState = QuorumState.COLLECTING
    votes: dict[str, QuorumVote] = field(default_factory=dict)
    rejected_votes: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        _safe_id(self.incident_id, "incident_id")
        if len(self.evidence_digest) != 64:
            raise ValueError("evidence_digest must be a SHA-256 hex digest")
        if self.required_confirmations < 1:
            raise ValueError("required_confirmations must be positive")
        if not self.expected_voters:
            raise ValueError("expected_voters cannot be empty")
        if self.required_confirmations > len(self.expected_voters):
            raise ValueError("required_confirmations cannot exceed expected voters")
        if self.deadline_at <= self.started_at:
            raise ValueError("deadline_at must be after started_at")

    def vote_counts(self) -> dict[str, int]:
        return {
            decision.value: sum(
                1 for vote in self.votes.values() if vote.decision == decision
            )
            for decision in VoteDecision
        }

    def snapshot(self) -> dict[str, Any]:
        counts = self.vote_counts()
        return {
            "incident_id": self.incident_id,
            "evidence_digest": self.evidence_digest,
            "required_confirmations": self.required_confirmations,
            "expected_voters": sorted(self.expected_voters),
            "started_at": self.started_at,
            "deadline_at": self.deadline_at,
            "state": self.state.value,
            "vote_counts": counts,
            "votes": [self.votes[key].to_dict() for key in sorted(self.votes)],
            "rejected_votes": list(self.rejected_votes),
        }

    def digest(self) -> str:
        return hashlib.sha256(_canonical(self.snapshot())).hexdigest()


class QuorumStateMachine:
    """Leader-coordinated N-of-M quorum state machine.

    The coordinator may collect votes, but it cannot bypass this state machine.
    A trusted controller must enforce the resulting state before physical action.
    """

    def __init__(self) -> None:
        self.incidents: dict[str, QuorumIncident] = {}

    def start(
        self,
        *,
        incident_id: str,
        evidence_digest: str,
        expected_voters: Iterable[str],
        required_confirmations: int,
        started_at: float,
        deadline_seconds: float,
    ) -> QuorumIncident:
        voters = frozenset(_safe_id(voter, "voter_id") for voter in expected_voters)
        if incident_id in self.incidents:
            raise ValueError("incident already exists")
        if deadline_seconds <= 0:
            raise ValueError("deadline_seconds must be positive")
        incident = QuorumIncident(
            incident_id=incident_id,
            evidence_digest=evidence_digest,
            required_confirmations=required_confirmations,
            expected_voters=voters,
            started_at=float(started_at),
            deadline_at=float(started_at) + float(deadline_seconds),
        )
        self.incidents[incident_id] = incident
        return incident

    def add_vote(self, vote: QuorumVote) -> QuorumState:
        incident = self.incidents.get(vote.incident_id)
        if incident is None:
            raise ValueError("unknown incident")
        if incident.state != QuorumState.COLLECTING:
            incident.rejected_votes.append({"reason": "incident_not_collecting", **vote.to_dict()})
            return incident.state
        if not vote.authenticated or not vote.fresh:
            incident.rejected_votes.append({"reason": "unauthenticated_or_stale", **vote.to_dict()})
            return incident.state
        if vote.voter_id not in incident.expected_voters:
            incident.rejected_votes.append({"reason": "unknown_voter", **vote.to_dict()})
            return incident.state
        if vote.evidence_digest != incident.evidence_digest:
            incident.rejected_votes.append({"reason": "evidence_digest_mismatch", **vote.to_dict()})
            return incident.state
        if vote.voter_id in incident.votes:
            incident.rejected_votes.append({"reason": "duplicate_voter", **vote.to_dict()})
            return incident.state
        if vote.received_at > incident.deadline_at:
            incident.rejected_votes.append({"reason": "vote_after_deadline", **vote.to_dict()})
            return incident.state

        incident.votes[vote.voter_id] = vote
        return self._recompute(incident, vote.received_at)

    def advance_time(self, incident_id: str, now: float) -> QuorumState:
        incident = self._get(incident_id)
        if incident.state == QuorumState.COLLECTING and now >= incident.deadline_at:
            incident.state = QuorumState.TIMEOUT
        return incident.state

    def mark_recovery_required(self, incident_id: str) -> QuorumState:
        incident = self._get(incident_id)
        incident.state = QuorumState.RECOVERY_REQUIRED
        return incident.state

    def snapshot(self, incident_id: str) -> dict[str, Any]:
        return self._get(incident_id).snapshot()

    def _recompute(self, incident: QuorumIncident, now: float) -> QuorumState:
        counts = incident.vote_counts()
        confirms = counts[VoteDecision.CONFIRM.value]
        denies = counts[VoteDecision.DENY.value]
        if confirms and denies:
            incident.state = QuorumState.CONFLICT
        elif confirms >= incident.required_confirmations:
            incident.state = QuorumState.APPROVED
        elif denies >= incident.required_confirmations:
            incident.state = QuorumState.DENIED
        elif now >= incident.deadline_at:
            incident.state = QuorumState.TIMEOUT
        return incident.state

    def _get(self, incident_id: str) -> QuorumIncident:
        try:
            return self.incidents[incident_id]
        except KeyError as exc:
            raise ValueError("unknown incident") from exc


__all__ = [
    "QuorumIncident",
    "QuorumState",
    "QuorumStateMachine",
    "QuorumVote",
    "VoteDecision",
]
