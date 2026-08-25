import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "integration"))
sys.path.insert(0, str(ROOT / "m3-ml-ledger" / "src"))

from integration.phase2_vertical_slice import Phase2VerticalSlice  # noqa: E402
from integration.telemetry import EventStatus, JsonlTelemetryReader, NormalizedTelemetry  # noqa: E402


def test_normalized_telemetry_round_trip():
    telemetry = NormalizedTelemetry(
        event_id="evt-1",
        event_type="evidence_pending",
        status=EventStatus.PENDING.value,
        controller_state="ALERT_PENDING",
        signals=[{"source_id": "known-detector", "authenticated": True, "fresh": True}],
        quorum_state="COLLECTING",
    )
    restored = NormalizedTelemetry.from_json(telemetry.to_json())
    assert restored.to_dict() == telemetry.to_dict()


def test_phase2_vertical_slice_emits_required_states(tmp_path):
    output = tmp_path / "phase2.jsonl"
    runner = Phase2VerticalSlice(output)
    events = runner.run()

    assert len(events) == 9
    assert output.exists()
    assert len(JsonlTelemetryReader(output).read_new()) == 9
    statuses = {event.status for event in events}
    assert {
        EventStatus.NORMAL.value,
        EventStatus.PENDING.value,
        EventStatus.APPROVED.value,
        EventStatus.REPLAY.value,
        EventStatus.STALE.value,
        EventStatus.CONFLICT.value,
        EventStatus.RECEIPT.value,
        EventStatus.RECOVERY.value,
    } <= statuses

    approved = next(event for event in events if event.status == EventStatus.APPROVED.value)
    assert approved.relay_state == "ISOLATED"
    assert approved.receipt_status == "VALID"
    assert approved.quorum_state == "APPROVED"
    assert len(approved.signals) == 2
    assert approved.transport_auth == "VERIFIED"
    assert approved.freshness_status == "FRESH"
    assert approved.transport_sequence is not None

    replay = next(event for event in events if event.status == EventStatus.REPLAY.value)
    assert replay.rejection_reason == "REPLAYED"
    stale = next(event for event in events if event.status == EventStatus.STALE.value)
    assert stale.rejection_reason == "STALE"
    conflict = next(event for event in events if event.status == EventStatus.CONFLICT.value)
    assert conflict.quorum_state == "CONFLICT"
    recovery = next(event for event in events if event.status == EventStatus.RECOVERY.value)
    assert recovery.recovery_state == "AUTHENTICATION_REQUIRED"
