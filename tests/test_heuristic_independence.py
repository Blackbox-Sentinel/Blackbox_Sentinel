"""Proves the second evidence signal is independent of volume features.

The M3 acceptance row "Strictly independent detection bases" was PENDING
because the heuristic and the ML model both consumed packets_per_sec. These
tests assert the heuristic now decides on TCP protocol state and payload-size
distribution only, and that volume can vary freely without changing it.
"""
import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sentinel_pipeline import _heuristic_protocol_state_check

VOLUME_FEATURES = {"packets_per_sec", "bytes_per_sec", "packet_count"}


def _benign_window(**overrides):
    base = {
        "syn_ratio": 0.20, "ack_ratio": 0.18, "rst_ratio": 0.02,
        "std_packet_size": 420.0, "p95_packet_size": 1400.0,
        "tcp_count": 200.0,
    }
    base.update(overrides)
    return base


def test_executable_code_never_reads_a_volume_feature():
    """Static proof: no volume feature appears in executable code."""
    src = Path(__file__).resolve().parents[1].joinpath("sentinel_pipeline.py").read_text()
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef)
              and n.name == "_heuristic_protocol_state_check")
    body = fn.body[1:] if (fn.body and isinstance(fn.body[0], ast.Expr)
                           and isinstance(fn.body[0].value, ast.Constant)) else fn.body
    found = {s.value for n in body for s in ast.walk(n)
             if isinstance(s, ast.Constant) and isinstance(s.value, str)} & VOLUME_FEATURES
    assert not found, f"heuristic still reads volume feature(s): {found}"


def test_decision_is_invariant_to_packet_rate():
    """Behavioural proof: 1 pkt/s and 100000 pkts/s give identical results."""
    quiet = _heuristic_protocol_state_check(
        _benign_window() | {"packets_per_sec": 1.0, "bytes_per_sec": 500.0})
    flood = _heuristic_protocol_state_check(
        _benign_window() | {"packets_per_sec": 100000.0, "bytes_per_sec": 9e7})
    assert quiet == flood, "volume changed the heuristic's output"


def test_benign_protocol_state_denies():
    r = _heuristic_protocol_state_check(_benign_window())
    assert r["is_anomalous_protocol_state"] is False
    assert r["triggered_signatures"] == []


def test_half_open_flood_confirms():
    """SYN far exceeding ACK is a handshake signature, not a volume one."""
    r = _heuristic_protocol_state_check(
        _benign_window(syn_ratio=0.95, ack_ratio=0.05))
    assert r["is_anomalous_protocol_state"] is True
    assert "half_open_flood" in r["triggered_signatures"]


def test_rst_storm_confirms():
    r = _heuristic_protocol_state_check(_benign_window(rst_ratio=0.80))
    assert "rst_storm" in r["triggered_signatures"]


def test_uniform_payload_confirms():
    """Near-identical packet sizes indicate automation/tunnelling."""
    r = _heuristic_protocol_state_check(
        _benign_window(std_packet_size=2.0, p95_packet_size=1400.0))
    assert "uniform_payload" in r["triggered_signatures"]


def test_small_sample_fails_closed():
    """A 3-packet window must not trigger on trivially extreme ratios."""
    r = _heuristic_protocol_state_check(
        _benign_window(syn_ratio=1.0, ack_ratio=0.0, rst_ratio=1.0, tcp_count=3.0))
    assert r["sufficient_sample"] is False
    assert r["is_anomalous_protocol_state"] is False


def test_missing_features_fail_closed():
    r = _heuristic_protocol_state_check({})
    assert r["is_anomalous_protocol_state"] is False
