"""Fast flow-identity-labeled dataset builder using raw PCAP parsing.

This version avoids Scapy packet-object construction for every packet. It reads
classic libpcap records with the standard library, parses Ethernet/IPv4/TCP/UDP
headers directly, labels packets by undirected flow identity, and emits the same
45-feature representation as feature_pipeline_v2.py. Existing data and models
are never overwritten unless the caller explicitly selects an existing output.
"""

from __future__ import annotations

import argparse
import csv
import ipaddress
import math
import struct
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from feature_pipeline_v2 import add_rolling_features, model_feature_columns


DEFAULT_FLOW_CSV = Path("..") / "datasets" / "CICIDS2017" / "attacks" / "Wednesday-workingHours.pcap_ISCX.csv"
DEFAULT_OUTPUT_DIR = Path("..") / "datasets" / "CICIDS2017" / "flow_labeled_v3_fast"
DEFAULT_PCAP = Path(
    r"C:\Users\SHASHWAT\.cache\huggingface\hub\datasets--bvsam--cic-ids-2017"
    r"\snapshots\70bac6246d99cf046186a02e1cce6883e2ffe7ea\pcap\Wednesday-workingHours.pcap"
)
HISTORY_WINDOWS = 5


@dataclass(slots=True)
class ParsedPacket:
    timestamp: float
    length: int
    source_ip: str | None
    destination_ip: str | None
    protocol: int | None
    source_port: int
    destination_port: int
    tcp_flags: int
    flow_key: tuple | None


def normalize_header(value: str) -> str:
    return " ".join(value.strip().lower().split())


def find_index(header: list[str], name: str) -> int:
    normalized = [normalize_header(value) for value in header]
    try:
        return normalized.index(normalize_header(name))
    except ValueError as error:
        raise ValueError(f"Missing required flow column: {name}") from error


def parse_port(value: str) -> int:
    try:
        return int(float(value.strip() or 0))
    except ValueError:
        return 0


def undirected_key(
    source_ip: str,
    source_port: int,
    destination_ip: str,
    destination_port: int,
    protocol: int,
) -> tuple:
    endpoints = sorted(
        [(source_ip.strip(), source_port), (destination_ip.strip(), destination_port)]
    )
    return endpoints[0], endpoints[1], protocol


def load_flow_labels(flow_csv: Path) -> tuple[set[tuple], dict[tuple, set[str]], dict]:
    all_keys: set[tuple] = set()
    attack_types_by_key: dict[tuple, set[str]] = defaultdict(set)
    counters = {
        "rows_seen": 0,
        "invalid_rows": 0,
        "benign_flows": 0,
        "attack_flows": 0,
    }

    with flow_csv.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if not header:
            raise ValueError(f"Flow CSV has no header: {flow_csv}")

        source_ip_index = find_index(header, "Source IP")
        source_port_index = find_index(header, "Source Port")
        destination_ip_index = find_index(header, "Destination IP")
        destination_port_index = find_index(header, "Destination Port")
        protocol_index = find_index(header, "Protocol")
        label_index = find_index(header, "Label")
        maximum_index = max(
            source_ip_index,
            source_port_index,
            destination_ip_index,
            destination_port_index,
            protocol_index,
            label_index,
        )

        for row in reader:
            counters["rows_seen"] += 1
            if len(row) <= maximum_index:
                counters["invalid_rows"] += 1
                continue

            key = undirected_key(
                row[source_ip_index],
                parse_port(row[source_port_index]),
                row[destination_ip_index],
                parse_port(row[destination_port_index]),
                parse_port(row[protocol_index]),
            )
            all_keys.add(key)
            label = row[label_index].strip()
            if label.upper() == "BENIGN":
                counters["benign_flows"] += 1
            else:
                counters["attack_flows"] += 1
                attack_types_by_key[key].add(label)

    counters["unique_flow_keys"] = len(all_keys)
    counters["unique_attack_keys"] = len(attack_types_by_key)
    return all_keys, attack_types_by_key, counters


def parse_packet(data: bytes, timestamp: float, original_length: int) -> ParsedPacket:
    packet_length = int(original_length or len(data))
    if len(data) < 14:
        return ParsedPacket(timestamp, packet_length, None, None, None, 0, 0, 0, None)

    ethernet_offset = 14
    ether_type = struct.unpack("!H", data[12:14])[0]
    while ether_type in {0x8100, 0x88A8, 0x9100} and len(data) >= ethernet_offset + 4:
        ether_type = struct.unpack("!H", data[ethernet_offset + 2:ethernet_offset + 4])[0]
        ethernet_offset += 4

    if ether_type != 0x0800 or len(data) < ethernet_offset + 20:
        return ParsedPacket(timestamp, packet_length, None, None, None, 0, 0, 0, None)

    ip_offset = ethernet_offset
    version_ihl = data[ip_offset]
    if version_ihl >> 4 != 4:
        return ParsedPacket(timestamp, packet_length, None, None, None, 0, 0, 0, None)

    ip_header_length = (version_ihl & 0x0F) * 4
    if ip_header_length < 20 or len(data) < ip_offset + ip_header_length:
        return ParsedPacket(timestamp, packet_length, None, None, None, 0, 0, 0, None)

    protocol = int(data[ip_offset + 9])
    source_ip = str(ipaddress.ip_address(data[ip_offset + 12:ip_offset + 16]))
    destination_ip = str(ipaddress.ip_address(data[ip_offset + 16:ip_offset + 20]))
    transport_offset = ip_offset + ip_header_length
    source_port = destination_port = 0
    tcp_flags = 0

    if protocol == 6 and len(data) >= transport_offset + 14:
        source_port, destination_port = struct.unpack(
            "!HH", data[transport_offset:transport_offset + 4]
        )
        tcp_flags = int(data[transport_offset + 13])
    elif protocol == 17 and len(data) >= transport_offset + 8:
        source_port, destination_port = struct.unpack(
            "!HH", data[transport_offset:transport_offset + 4]
        )

    key = undirected_key(
        source_ip,
        source_port,
        destination_ip,
        destination_port,
        protocol,
    )
    return ParsedPacket(
        timestamp,
        packet_length,
        source_ip,
        destination_ip,
        protocol,
        source_port,
        destination_port,
        tcp_flags,
        key,
    )


def pcap_format(magic: bytes) -> tuple[str, str]:
    formats = {
        b"\xd4\xc3\xb2\xa1": ("<", "microseconds"),
        b"\xa1\xb2\xc3\xd4": (">", "microseconds"),
        b"\x4d\x3c\xb2\xa1": ("<", "nanoseconds"),
        b"\xa1\xb2\x3c\x4d": (">", "nanoseconds"),
    }
    if magic not in formats:
        raise ValueError(f"Unsupported classic PCAP magic: {magic.hex()}")
    return formats[magic]


def iter_classic_pcap(handle):
    header = handle.read(24)
    if len(header) < 24:
        raise ValueError("Classic PCAP header is truncated")
    endian, precision = pcap_format(header[:4])
    record_format = endian + "IIII"
    record_size = struct.calcsize(record_format)
    while True:
        record = handle.read(record_size)
        if not record or len(record) < record_size:
            return
        ts_sec, ts_fraction, included_length, original_length = struct.unpack(record_format, record)
        payload = handle.read(included_length)
        if len(payload) < included_length:
            return
        divisor = 1_000_000_000 if precision == "nanoseconds" else 1_000_000
        yield payload, float(ts_sec) + ts_fraction / divisor, original_length


def parse_interface_tsresol(block: bytes, endian: str) -> float:
    resolution = 1e-6
    option_offset = 16
    option_limit = len(block) - 4
    while option_offset + 4 <= option_limit:
        option_code, option_length = struct.unpack(
            endian + "HH", block[option_offset:option_offset + 4]
        )
        if option_code == 0:
            break
        value_start = option_offset + 4
        value_end = value_start + option_length
        if value_end > option_limit:
            break
        if option_code == 9 and option_length >= 1:
            raw = block[value_start]
            resolution = 2.0 ** -(raw & 0x7F) if raw & 0x80 else 10.0 ** -raw
        option_offset += 4 + ((option_length + 3) // 4) * 4
    return resolution


def iter_pcapng(handle):
    first = handle.read(12)
    if len(first) < 12 or first[:4] != b"\x0a\x0d\x0d\x0a":
        raise ValueError("PCAPNG section header is missing")
    byte_order_magic = first[8:12]
    if byte_order_magic == b"\x1a\x2b\x3c\x4d":
        endian = ">"
    elif byte_order_magic == b"\x4d\x3c\x2b\x1a":
        endian = "<"
    else:
        raise ValueError(f"Unsupported PCAPNG byte-order magic: {byte_order_magic.hex()}")

    total_length = struct.unpack(endian + "I", first[4:8])[0]
    if total_length < 12:
        raise ValueError("Invalid PCAPNG section length")
    remaining = handle.read(total_length - 12)
    if len(remaining) < total_length - 12:
        return

    interface_resolutions: list[float] = []
    while True:
        block_header = handle.read(8)
        if not block_header or len(block_header) < 8:
            return
        block_type, total_length = struct.unpack(endian + "II", block_header)
        if total_length < 12:
            raise ValueError(f"Invalid PCAPNG block length: {total_length}")
        block_body = handle.read(total_length - 8)
        if len(block_body) < total_length - 8:
            return
        block = block_header + block_body

        if block_type == 0x00000001:  # Interface Description Block
            interface_resolutions.append(parse_interface_tsresol(block, endian))
        elif block_type == 0x00000006:  # Enhanced Packet Block
            if len(block) < 32:
                continue
            interface_id, timestamp_high, timestamp_low, captured_length, original_length = struct.unpack(
                endian + "IIIII", block[8:28]
            )
            payload = block[28:28 + captured_length]
            if interface_id < len(interface_resolutions):
                resolution = interface_resolutions[interface_id]
            else:
                resolution = 1e-6
            ticks = (timestamp_high << 32) | timestamp_low
            yield payload, ticks * resolution, original_length
        elif block_type == 0x00000002:  # Legacy Packet Block
            if len(block) < 32:
                continue
            interface_id, timestamp_high, timestamp_low, captured_length, original_length = struct.unpack(
                endian + "IIIII", block[8:28]
            )
            payload = block[32:32 + captured_length]
            resolution = interface_resolutions[interface_id] if interface_id < len(interface_resolutions) else 1e-6
            ticks = (timestamp_high << 32) | timestamp_low
            yield payload, ticks * resolution, original_length


def iter_capture_records(pcap_path: Path):
    with pcap_path.open("rb") as handle:
        magic = handle.read(4)
        handle.seek(0)
        if magic == b"\x0a\x0d\x0d\x0a":
            yield from iter_pcapng(handle)
        else:
            yield from iter_classic_pcap(handle)


def window_features_fast(packets: list[ParsedPacket], window_start: float) -> dict:
    sizes = np.asarray([packet.length for packet in packets], dtype=float)
    source_ips = [packet.source_ip for packet in packets if packet.source_ip is not None]
    destination_ips = [packet.destination_ip for packet in packets if packet.destination_ip is not None]
    tcp_count = sum(packet.protocol == 6 for packet in packets)
    udp_count = sum(packet.protocol == 17 for packet in packets)
    icmp_count = sum(packet.protocol == 1 for packet in packets)
    tcp_denominator = max(tcp_count, 1)
    packet_count = len(packets)

    syn_count = sum(bool(packet.tcp_flags & 0x02) for packet in packets if packet.protocol == 6)
    ack_count = sum(bool(packet.tcp_flags & 0x10) for packet in packets if packet.protocol == 6)
    fin_count = sum(bool(packet.tcp_flags & 0x01) for packet in packets if packet.protocol == 6)
    rst_count = sum(bool(packet.tcp_flags & 0x04) for packet in packets if packet.protocol == 6)
    psh_count = sum(bool(packet.tcp_flags & 0x08) for packet in packets if packet.protocol == 6)
    urg_count = sum(bool(packet.tcp_flags & 0x20) for packet in packets if packet.protocol == 6)

    def entropy(values: list[str | None]) -> float:
        counts = Counter(value for value in values if value is not None)
        total = sum(counts.values())
        if not total:
            return 0.0
        return float(-sum((count / total) * math.log2(count / total) for count in counts.values()))

    def ratio(value: float, denominator: float) -> float:
        return float(value / denominator) if denominator else 0.0

    if len(sizes):
        avg = float(sizes.mean())
        std = float(sizes.std())
        p95 = float(np.percentile(sizes, 95))
        maximum = int(sizes.max())
        minimum = int(sizes.min())
    else:
        avg = std = p95 = 0.0
        maximum = minimum = 0

    return {
        "packets_per_sec": float(packet_count),
        "bytes_per_sec": float(sizes.sum()),
        "avg_packet_size": avg,
        "std_packet_size": std,
        "p95_packet_size": p95,
        "max_packet_size": maximum,
        "min_packet_size": minimum,
        "tcp_count": int(tcp_count),
        "udp_count": int(udp_count),
        "icmp_count": int(icmp_count),
        "tcp_ratio": ratio(tcp_count, packet_count),
        "udp_ratio": ratio(udp_count, packet_count),
        "icmp_ratio": ratio(icmp_count, packet_count),
        "unique_src_ips": len(set(source_ips)),
        "unique_dst_ips": len(set(destination_ips)),
        "src_ip_entropy": entropy(source_ips),
        "dst_ip_entropy": entropy(destination_ips),
        "syn_count": int(syn_count),
        "ack_count": int(ack_count),
        "fin_count": int(fin_count),
        "rst_count": int(rst_count),
        "psh_count": int(psh_count),
        "urg_count": int(urg_count),
        "syn_ratio": ratio(syn_count, tcp_denominator),
        "ack_ratio": ratio(ack_count, tcp_denominator),
        "fin_ratio": ratio(fin_count, tcp_denominator),
        "rst_ratio": ratio(rst_count, tcp_denominator),
        "psh_ratio": ratio(psh_count, tcp_denominator),
        "urg_ratio": ratio(urg_count, tcp_denominator),
        "window_start_epoch": float(window_start),
        "timestamp": datetime.fromtimestamp(window_start, tz=timezone.utc).isoformat(),
    }


def pcap_windows(
    pcap_path: Path,
    all_flow_keys: set[tuple],
    attack_types_by_key: dict[tuple, set[str]],
    max_packets: int | None,
    skip_packets: int,
    max_windows: int | None,
):
    packet_index = 0
    emitted_windows = 0
    current_second: int | None = None
    packets: list[ParsedPacket] = []
    matched_count = 0
    attack_count = 0
    unmatched_count = 0
    attack_types: set[str] = set()
    print("PCAP parser: raw classic-PCAP/PCAPNG reader", flush=True)

    for payload, timestamp, original_length in iter_capture_records(pcap_path):
        packet_index += 1
        if packet_index <= skip_packets:
            continue
        if max_packets is not None and packet_index > skip_packets + max_packets:
            break
        if packet_index % 250000 == 0:
            print(
                f"  packets scanned: {packet_index} | windows emitted: {emitted_windows}",
                flush=True,
            )

        parsed = parse_packet(payload, timestamp, original_length)
        second = int(timestamp)
        if current_second is None:
            current_second = second

        while second > current_second:
            if packets:
                row = window_features_fast(packets, float(current_second))
                row["matched_packet_count"] = matched_count
                row["attack_packet_count"] = attack_count
                row["unmatched_packet_count"] = unmatched_count
                row["attack_types"] = ";".join(sorted(attack_types))
                row["label_source"] = "undirected_flow_identity"
                row["label"] = int(attack_count > 0)
                emitted_windows += 1
                yield row
                if max_windows is not None and emitted_windows >= max_windows:
                    return
            packets = []
            matched_count = attack_count = unmatched_count = 0
            attack_types = set()
            current_second += 1

        packets.append(parsed)
        if parsed.flow_key is None or parsed.flow_key not in all_flow_keys:
            unmatched_count += 1
        else:
            matched_count += 1
            if parsed.flow_key in attack_types_by_key:
                attack_count += 1
                attack_types.update(attack_types_by_key[parsed.flow_key])

    if packets and (max_windows is None or emitted_windows < max_windows):
        row = window_features_fast(packets, float(current_second))
        row["matched_packet_count"] = matched_count
        row["attack_packet_count"] = attack_count
        row["unmatched_packet_count"] = unmatched_count
        row["attack_types"] = ";".join(sorted(attack_types))
        row["label_source"] = "undirected_flow_identity"
        row["label"] = int(attack_count > 0)
        yield row


def temporal_split(frame: pd.DataFrame, test_fraction: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_parts = []
    test_parts = []
    for _, group in frame.groupby("source_file", sort=False):
        group = group.sort_values("window_start_epoch", kind="stable")
        test_count = min(max(1, int(round(len(group) * test_fraction))), max(len(group) - 1, 0))
        if test_count == 0:
            train_parts.append(group)
            test_parts.append(group.iloc[0:0])
        else:
            train_parts.append(group.iloc[:-test_count])
            test_parts.append(group.iloc[-test_count:])
    return pd.concat(train_parts, ignore_index=True), pd.concat(test_parts, ignore_index=True)


def save_outputs(frame: pd.DataFrame, output_dir: Path, test_fraction: float) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    enriched = add_rolling_features(frame, history_windows=HISTORY_WINDOWS, group_column="source_file")
    enriched = enriched[
        [
            "timestamp",
            "window_start_epoch",
            "source_file",
            "label_source",
            "attack_types",
            "matched_packet_count",
            "attack_packet_count",
            "unmatched_packet_count",
            *model_feature_columns(HISTORY_WINDOWS),
            "label",
        ]
    ]
    train, test = temporal_split(enriched, test_fraction)
    paths = {
        "all": output_dir / "pcap_flow_labeled_v3_all.csv",
        "train": output_dir / "pcap_flow_labeled_v3_train.csv",
        "test": output_dir / "pcap_flow_labeled_v3_test.csv",
    }
    enriched.to_csv(paths["all"], index=False)
    train.to_csv(paths["train"], index=False)
    test.to_csv(paths["test"], index=False)
    print("Generated outputs:")
    for name, path in paths.items():
        data = enriched if name == "all" else train if name == "train" else test
        print(f"  {name}: {path} | rows={len(data)} | labels={data['label'].value_counts().to_dict()}")
    print(f"Model features: {len(model_feature_columns(HISTORY_WINDOWS))}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flow-csv", type=Path, default=DEFAULT_FLOW_CSV)
    parser.add_argument("--pcap", type=Path, default=DEFAULT_PCAP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-packets", type=int, default=None)
    parser.add_argument("--skip-packets", type=int, default=0)
    parser.add_argument("--max-windows", type=int, default=None)
    parser.add_argument("--test-fraction", type=float, default=0.20)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.flow_csv.is_file():
        raise FileNotFoundError(args.flow_csv)
    if not args.pcap.is_file():
        raise FileNotFoundError(args.pcap)
    if args.max_packets is not None and args.max_packets < 1:
        raise ValueError("--max-packets must be positive")
    if args.skip_packets < 0:
        raise ValueError("--skip-packets cannot be negative")
    if not 0 < args.test_fraction < 1:
        raise ValueError("--test-fraction must be between 0 and 1")

    print("Loading flow identity labels...")
    all_flow_keys, attack_types_by_key, counters = load_flow_labels(args.flow_csv)
    for key in ("rows_seen", "invalid_rows", "benign_flows", "attack_flows", "unique_flow_keys", "unique_attack_keys"):
        print(f"  {key}: {counters[key]}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    print(
        f"Reading PCAP windows | skip_packets={args.skip_packets} | "
        f"max_packets={args.max_packets or 'unlimited'} | max_windows={args.max_windows or 'unlimited'}"
    )
    for row in pcap_windows(
        args.pcap,
        all_flow_keys,
        attack_types_by_key,
        max_packets=args.max_packets,
        skip_packets=args.skip_packets,
        max_windows=args.max_windows,
    ):
        row["source_file"] = args.pcap.name
        rows.append(row)

    if not rows:
        raise RuntimeError("No windows were emitted")
    frame = pd.DataFrame(rows)
    print(
        f"Windows emitted: {len(frame)} | labels={frame['label'].value_counts().to_dict()} | "
        f"matched packets={int(frame['matched_packet_count'].sum())} | "
        f"attack packets={int(frame['attack_packet_count'].sum())}"
    )
    save_outputs(frame, args.output_dir, args.test_fraction)
    print("Dataset build complete. Existing datasets and models were not touched.")


if __name__ == "__main__":
    main()
