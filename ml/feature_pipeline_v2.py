"""Shared packet-to-window feature extraction for PCAP and live traffic.

The functions in this module are deliberately shared by the offline dataset
builder and future live inference code so that training and deployment use the
same feature definitions.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import numpy as np
import pandas as pd
from scapy.all import ICMP, IP, TCP, UDP, PcapReader, sniff


BASE_FEATURE_COLUMNS = [
    "packets_per_sec",
    "bytes_per_sec",
    "avg_packet_size",
    "std_packet_size",
    "p95_packet_size",
    "max_packet_size",
    "min_packet_size",
    "tcp_count",
    "udp_count",
    "icmp_count",
    "tcp_ratio",
    "udp_ratio",
    "icmp_ratio",
    "unique_src_ips",
    "unique_dst_ips",
    "src_ip_entropy",
    "dst_ip_entropy",
    "syn_count",
    "ack_count",
    "fin_count",
    "rst_count",
    "psh_count",
    "urg_count",
    "syn_ratio",
    "ack_ratio",
    "fin_ratio",
    "rst_ratio",
    "psh_ratio",
    "urg_ratio",
]

ROLLING_SPECS = {
    "packets_per_sec": ("mean", "std", "max"),
    "bytes_per_sec": ("mean", "std", "max"),
    "unique_src_ips": ("mean", "max"),
    "unique_dst_ips": ("mean", "max"),
    "syn_ratio": ("mean", "max"),
    "rst_ratio": ("mean", "max"),
    "tcp_ratio": ("mean",),
}

METADATA_COLUMNS = ["timestamp", "window_start_epoch", "source_file", "label"]


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _entropy(values: Iterable[str]) -> float:
    counts = pd.Series(list(values), dtype="object").value_counts()
    if counts.empty:
        return 0.0
    probabilities = counts.to_numpy(dtype=float) / counts.sum()
    return float(-(probabilities * np.log2(probabilities)).sum())


def _packet_timestamp(packet) -> float | None:
    try:
        return float(packet.time)
    except (AttributeError, TypeError, ValueError):
        return None


def window_features(
    packets: Sequence,
    window_start_epoch: float,
    window_seconds: float = 1.0,
) -> dict:
    """Extract numeric features from one fixed-duration packet window."""
    packet_sizes: list[int] = []
    source_ips: list[str] = []
    destination_ips: list[str] = []

    tcp_count = udp_count = icmp_count = 0
    syn_count = ack_count = fin_count = rst_count = psh_count = urg_count = 0

    for packet in packets:
        size = int(len(packet))
        packet_sizes.append(size)

        if IP not in packet:
            continue

        source_ips.append(str(packet[IP].src))
        destination_ips.append(str(packet[IP].dst))

        if TCP in packet:
            tcp_count += 1
            flags = int(packet[TCP].flags)
            syn_count += int(bool(flags & 0x02))
            ack_count += int(bool(flags & 0x10))
            fin_count += int(bool(flags & 0x01))
            rst_count += int(bool(flags & 0x04))
            psh_count += int(bool(flags & 0x08))
            urg_count += int(bool(flags & 0x20))
        elif UDP in packet:
            udp_count += 1
        elif ICMP in packet:
            icmp_count += 1

    packet_count = len(packet_sizes)
    total_bytes = sum(packet_sizes)
    tcp_denominator = tcp_count
    duration = max(float(window_seconds), 1e-9)

    if packet_sizes:
        sizes = np.asarray(packet_sizes, dtype=float)
        avg_packet_size = float(sizes.mean())
        std_packet_size = float(sizes.std())
        p95_packet_size = float(np.percentile(sizes, 95))
        max_packet_size = int(sizes.max())
        min_packet_size = int(sizes.min())
    else:
        avg_packet_size = std_packet_size = p95_packet_size = 0.0
        max_packet_size = min_packet_size = 0

    feature_row = {
        "packet_count": packet_count,
        "packets_per_sec": packet_count / duration,
        "bytes_per_sec": total_bytes / duration,
        "avg_packet_size": avg_packet_size,
        "std_packet_size": std_packet_size,
        "p95_packet_size": p95_packet_size,
        "max_packet_size": max_packet_size,
        "min_packet_size": min_packet_size,
        "tcp_count": tcp_count,
        "udp_count": udp_count,
        "icmp_count": icmp_count,
        "tcp_ratio": _safe_ratio(tcp_count, packet_count),
        "udp_ratio": _safe_ratio(udp_count, packet_count),
        "icmp_ratio": _safe_ratio(icmp_count, packet_count),
        "unique_src_ips": len(set(source_ips)),
        "unique_dst_ips": len(set(destination_ips)),
        "src_ip_entropy": _entropy(source_ips),
        "dst_ip_entropy": _entropy(destination_ips),
        "syn_count": syn_count,
        "ack_count": ack_count,
        "fin_count": fin_count,
        "rst_count": rst_count,
        "psh_count": psh_count,
        "urg_count": urg_count,
        "syn_ratio": _safe_ratio(syn_count, tcp_denominator),
        "ack_ratio": _safe_ratio(ack_count, tcp_denominator),
        "fin_ratio": _safe_ratio(fin_count, tcp_denominator),
        "rst_ratio": _safe_ratio(rst_count, tcp_denominator),
        "psh_ratio": _safe_ratio(psh_count, tcp_denominator),
        "urg_ratio": _safe_ratio(urg_count, tcp_denominator),
    }

    feature_row["window_start_epoch"] = float(window_start_epoch)
    feature_row["timestamp"] = datetime.fromtimestamp(
        window_start_epoch,
        tz=timezone.utc,
    ).isoformat()
    return feature_row


def iter_pcap_windows(
    pcap_path: str | Path,
    window_seconds: float = 1.0,
    max_windows: int | None = None,
    include_empty: bool = False,
) -> Iterator[tuple[float, list]]:
    """Yield packets grouped by actual capture time, not packet count."""
    if window_seconds <= 0:
        raise ValueError("window_seconds must be positive")

    current_window_start: float | None = None
    current_packets: list = []
    emitted_windows = 0

    with PcapReader(str(pcap_path)) as reader:
        for packet in reader:
            timestamp = _packet_timestamp(packet)
            if timestamp is None:
                continue

            if current_window_start is None:
                current_window_start = (
                    np.floor(timestamp / window_seconds) * window_seconds
                )

            while timestamp >= current_window_start + window_seconds:
                if current_packets or include_empty:
                    yield current_window_start, current_packets
                    emitted_windows += 1
                    if max_windows is not None and emitted_windows >= max_windows:
                        return

                current_window_start += window_seconds
                current_packets = []

            current_packets.append(packet)

    if current_window_start is not None and (current_packets or include_empty):
        yield current_window_start, current_packets


def add_rolling_features(
    frame: pd.DataFrame,
    history_windows: int = 5,
    group_column: str = "source_file",
) -> pd.DataFrame:
    """Add past-window statistics without using future windows.

    The current row is excluded from the rolling history by shifting the
    rolling result by one row. For the first row of a source, the current value
    is used as a deterministic fallback because no history exists yet.
    """
    if history_windows < 1:
        raise ValueError("history_windows must be at least 1")

    output = frame.copy()
    if "window_start_epoch" in output.columns:
        output = output.sort_values(
            [group_column, "window_start_epoch"],
            kind="stable",
        ).reset_index(drop=True)

    groups = output.groupby(group_column, sort=False, dropna=False)
    for base_column, aggregations in ROLLING_SPECS.items():
        for aggregation in aggregations:
            name = f"{base_column}_history_{history_windows}w_{aggregation}"
            rolling = groups[base_column].transform(
                lambda series: getattr(
                    series.rolling(history_windows, min_periods=1),
                    aggregation,
                )().shift(1)
            )
            output[name] = rolling.fillna(output[base_column]).astype(float)

    output[f"history_window_count_{history_windows}w"] = groups["source_file"].cumcount().clip(
        upper=history_windows
    )
    return output


class RollingFeatureState:
    """Maintain the same past-window features for live inference."""

    def __init__(self, history_windows: int = 5):
        if history_windows < 1:
            raise ValueError("history_windows must be at least 1")
        self.history_windows = history_windows
        self._history: deque[dict] = deque(maxlen=history_windows)

    def enrich(self, current_row: dict) -> dict:
        output = dict(current_row)
        history = list(self._history)

        for base_column, aggregations in ROLLING_SPECS.items():
            values = [float(row[base_column]) for row in history]
            if not values:
                values = [float(current_row[base_column])]

            for aggregation in aggregations:
                if aggregation == "mean":
                    value = np.mean(values)
                elif aggregation == "std":
                    value = np.std(values)
                elif aggregation == "max":
                    value = np.max(values)
                else:
                    raise ValueError(f"Unsupported rolling aggregation: {aggregation}")
                output[f"{base_column}_history_{self.history_windows}w_{aggregation}"] = float(value)

        output[f"history_window_count_{self.history_windows}w"] = min(
            len(history), self.history_windows
        )
        self._history.append(dict(current_row))
        return output


def capture_live_window(
    timeout: float = 1.0,
    iface: str | None = None,
    history_state: RollingFeatureState | None = None,
) -> dict:
    """Capture one live window and return the same feature schema as PCAP data."""
    packets = sniff(iface=iface, timeout=timeout, store=True)
    timestamps = [
        timestamp
        for timestamp in (_packet_timestamp(packet) for packet in packets)
        if timestamp is not None
    ]
    window_start = min(timestamps) if timestamps else datetime.now(timezone.utc).timestamp()
    row = window_features(packets, window_start, timeout)
    if history_state is not None:
        row = history_state.enrich(row)
    return row


def model_feature_columns(history_windows: int = 5) -> list[str]:
    rolling_columns = [
        f"{base}_history_{history_windows}w_{aggregation}"
        for base, aggregations in ROLLING_SPECS.items()
        for aggregation in aggregations
    ]
    return BASE_FEATURE_COLUMNS + rolling_columns + [
        f"history_window_count_{history_windows}w"
    ]
