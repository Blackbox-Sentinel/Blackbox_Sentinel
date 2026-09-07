import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from security.trusted_controller import TrustedController


def test_one_signal_does_not_isolate():
    controller = TrustedController(secret=b"s" * 32, freshness_window_seconds=60)
    signal = controller.issue_signal(
        event_id="evt-1",
        source="m3-known",
        signal_type="known_attack",
        payload={"probability": 0.99},
        issued_at=100.0,
    )
    result = controller.submit_signal(signal, now=100.0)
    assert result["decision"] == "PENDING"
    assert result["state"] == "ALERT_PENDING"
    assert controller.relay_state == "ENGAGED"


def test_two_independent_signals_isolate_and_create_valid_receipt():
    controller = TrustedController(secret=b"s" * 32, freshness_window_seconds=60)
    first = controller.issue_signal(
        event_id="evt-2",
        source="m3-known",
        signal_type="known_attack",
        payload={"probability": 0.99},
        issued_at=100.0,
    )
    second = controller.issue_signal(
        event_id="evt-2",
        source="m3-adaptive",
        signal_type="adaptive_anomaly",
        payload={"score": -0.12},
        issued_at=100.0,
    )
    assert controller.submit_signal(first, now=100.0)["decision"] == "PENDING"
    result = controller.submit_signal(second, now=100.0)
    assert result["decision"] == "ISOLATE"
    assert result["state"] == "ISOLATED"
    assert result["relay_state"] == "ISOLATED"
    assert controller.verify_receipt(result["receipt"])[1] == "VALID"


def test_replayed_signal_is_rejected():
    controller = TrustedController(secret=b"s" * 32, freshness_window_seconds=60)
    signal = controller.issue_signal(
        event_id="evt-3",
        source="m3-known",
        signal_type="known_attack",
        payload={},
        issued_at=100.0,
    )
    assert controller.submit_signal(signal, now=100.0)["accepted"] is True
    replay = controller.submit_signal(signal, now=100.0)
    assert replay["accepted"] is False
    assert replay["reason"] in {"REPLAYED_OR_OUT_OF_ORDER", "DUPLICATE_EVENT"}


def test_quorum_is_required_when_configured():
    controller = TrustedController(secret=b"s" * 32, quorum_required=2, freshness_window_seconds=60)
    for source, signal_type in (("m3-known", "known_attack"), ("m3-adaptive", "adaptive_anomaly")):
        signal = controller.issue_signal(
            event_id="evt-4",
            source=source,
            signal_type=signal_type,
            payload={},
            issued_at=100.0,
        )
        controller.submit_signal(signal, now=100.0)
    vote_a = controller.issue_vote(event_id="evt-4", peer_id="peer-a", issued_at=100.0)
    vote_b = controller.issue_vote(event_id="evt-4", peer_id="peer-b", issued_at=100.0)
    assert controller.submit_vote(vote_a, now=100.0)["decision"] == "PENDING"
    result = controller.submit_vote(vote_b, now=100.0)
    assert result["decision"] == "ISOLATE"
    assert result["quorum_received"] == 2
