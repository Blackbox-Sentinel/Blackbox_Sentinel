"""
Regression tests for the capture/feature-extraction path in
ml/feature_pipeline_v2.py. Packets are constructed in-memory via Scapy
(IP()/TCP()/etc.) so these run without a live interface, Npcap, or admin
rights.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pytest
from scapy.all import ICMP, IP, TCP, UDP

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ml.feature_pipeline_v2 import (  # noqa: E402
    RollingFeatureState,
    model_feature_columns,
    window_features,
)


def _row(packets_per_sec, **overrides):
    """Minimal feature row covering every ROLLING_SPECS base column."""
    base = {
        "packets_per_sec": packets_per_sec,
        "bytes_per_sec": 0.0,
        "unique_src_ips": 0.0,
        "unique_dst_ips": 0.0,
        "syn_ratio": 0.0,
        "rst_ratio": 0.0,
        "tcp_ratio": 0.0,
    }
    base.update(overrides)
    return base


def test_rolling_feature_state_no_lookahead_and_bounded_history():
    """enrich() must compute rolling stats from PRIOR windows only, and must
    bound history to `history_windows` entries (oldest evicted first).

    An off-by-one refactor (computing history after appending current_row,
    or appending the enriched `output` instead of the raw `current_row`)
    would leak the current window into its own "past" average, or corrupt
    the history contents entirely.
    """
    state = RollingFeatureState(history_windows=3)

    # First call: history is empty. Must fall back to current_row's own
    # value (the `if not values:` branch) and must not raise.
    first = state.enrich(_row(10.0))
    assert first["packets_per_sec_history_3w_mean"] == pytest.approx(10.0)
    assert first["packets_per_sec_history_3w_std"] == pytest.approx(0.0)
    assert first["packets_per_sec_history_3w_max"] == pytest.approx(10.0)
    assert first["history_window_count_3w"] == 0

    second = state.enrich(_row(20.0))
    assert second["packets_per_sec_history_3w_mean"] == pytest.approx(10.0)
    assert second["history_window_count_3w"] == 1

    third = state.enrich(_row(30.0))
    assert third["packets_per_sec_history_3w_mean"] == pytest.approx(15.0)
    assert third["history_window_count_3w"] == 2

    fourth = state.enrich(_row(40.0))
    assert fourth["packets_per_sec_history_3w_mean"] == pytest.approx(20.0)
    assert fourth["history_window_count_3w"] == 3

    # Fifth call: history_windows=3, so the oldest raw value (10.0) must
    # already be evicted. An unbounded/leaking implementation would give
    # mean((10, 20, 30, 40)) == 25.0 instead of mean((20, 30, 40)) == 30.0.
    fifth = state.enrich(_row(50.0))
    assert fifth["packets_per_sec_history_3w_mean"] == pytest.approx(30.0)
    assert fifth["history_window_count_3w"] == 3


def test_model_feature_columns_matches_actual_pipeline_output():
    """model_feature_columns() must exactly match the keys produced by
    running real packets through window_features() + RollingFeatureState,
    excluding only the metadata/display fields (timestamp, window_start_epoch,
    packet_count) that ride in feature_row but are never selected into the
    model's input vector by AnomalyScorer.ingest_feature_window().

    This encodes, as a permanent regression test, two bugs found in this
    session: window_features() always adds window_start_epoch, which
    model_feature_columns() does not account for; and, separately,
    window_features() also adds packet_count as dashboard/display metadata
    (the raw per-window packet count, distinct from the packets_per_sec rate
    that is an actual model feature), which model_feature_columns() likewise
    does not account for.
    """
    packets = [
        IP(src="10.0.0.1", dst="10.0.0.100") / TCP(flags="S"),
        IP(src="10.0.0.2", dst="10.0.0.100") / UDP(),
    ]
    raw_row = window_features(packets, window_start_epoch=0.0, window_seconds=1.0)

    state = RollingFeatureState(history_windows=5)
    enriched_row = state.enrich(raw_row)

    actual_keys = set(enriched_row.keys()) - {"timestamp", "window_start_epoch", "packet_count"}
    expected_keys = set(model_feature_columns(history_windows=5))

    assert actual_keys == expected_keys


def test_window_features_packet_math_correctness():
    """Verify packet-parsing and ratio arithmetic against independently
    computed expected values, using a deterministic, crafted packet set.

    Flag bit-masking, ratio denominators (e.g. syn_ratio / tcp_count vs.
    packet_count), and entropy are all easy to get subtly wrong without
    ever raising an exception — a swapped denominator still produces a
    plausible-looking float in [0, 1].
    """
    packets = [
        IP(src="10.0.0.1", dst="10.0.0.100") / TCP(flags="S"),   # SYN only
        IP(src="10.0.0.1", dst="10.0.0.100") / TCP(flags="S"),   # SYN only (same src)
        IP(src="10.0.0.2", dst="10.0.0.100") / TCP(flags="SA"),  # SYN+ACK
        IP(src="10.0.0.3", dst="10.0.0.100") / UDP(),
        IP(src="10.0.0.4", dst="10.0.0.100") / ICMP(),
    ]

    row = window_features(packets, window_start_epoch=0.0, window_seconds=1.0)

    assert row["packets_per_sec"] == pytest.approx(5.0)
    assert row["tcp_count"] == 3
    assert row["udp_count"] == 1
    assert row["icmp_count"] == 1
    assert row["syn_count"] == 3
    assert row["ack_count"] == 1
    assert row["fin_count"] == 0
    assert row["rst_count"] == 0

    assert row["tcp_ratio"] == pytest.approx(3 / 5)
    assert row["udp_ratio"] == pytest.approx(1 / 5)
    assert row["icmp_ratio"] == pytest.approx(1 / 5)

    # syn_ratio/ack_ratio are denominated by tcp_count, NOT packet_count —
    # a swapped denominator here would still silently produce a valid ratio.
    assert row["syn_ratio"] == pytest.approx(3 / 3)
    assert row["ack_ratio"] == pytest.approx(1 / 3)

    assert row["unique_src_ips"] == 4
    assert row["unique_dst_ips"] == 1

    # Independently recomputed Shannon entropy for the known 2:1:1:1 source
    # IP distribution across 5 packets (not calling the module's _entropy()).
    expected_src_entropy = -sum(
        (count / 5) * math.log2(count / 5) for count in (2, 1, 1, 1)
    )
    assert row["src_ip_entropy"] == pytest.approx(expected_src_entropy)
    assert row["dst_ip_entropy"] == pytest.approx(0.0)  # single dest IP -> zero entropy

    expected_sizes = np.asarray([len(p) for p in packets], dtype=float)
    assert row["avg_packet_size"] == pytest.approx(expected_sizes.mean())
    assert row["std_packet_size"] == pytest.approx(expected_sizes.std())
    assert row["p95_packet_size"] == pytest.approx(np.percentile(expected_sizes, 95))
    assert row["max_packet_size"] == int(expected_sizes.max())
    assert row["min_packet_size"] == int(expected_sizes.min())
