"""Build a minute-level label map from a CICIDS flow-label CSV.

The CICIDS CSV contains duplicate column names, so this script uses the raw CSV
header and row positions instead of pandas or Import-Csv. Existing files are
never modified; only the requested output CSV is written.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


DEFAULT_FLOW_CSV = Path("..") / "datasets" / "CICIDS2017" / "attacks" / "Wednesday-workingHours.pcap_ISCX.csv"
DEFAULT_OUTPUT = Path("..") / "datasets" / "CICIDS2017" / "v2_label_map.csv"

# CICIDS2017 uses day/month/year for values such as 5/7/2017,
# corresponding to Wednesday, 5 July 2017.
TIMESTAMP_FORMATS = (
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)


def parse_timestamp(value: str) -> datetime:
    cleaned = value.strip()
    for timestamp_format in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(cleaned, timestamp_format)
        except ValueError:
            continue
    raise ValueError(f"Unsupported timestamp format: {value!r}")


def find_column_index(header: list[str], name: str) -> int:
    normalized = [cell.strip().lower() for cell in header]
    try:
        return normalized.index(name.lower())
    except ValueError as error:
        raise ValueError(f"Required column {name!r} was not found") from error


def build_label_map(flow_csv: Path) -> tuple[list[dict], dict[str, int]]:
    minutes: dict[datetime, dict] = defaultdict(
        lambda: {
            "label": 0,
            "attack_types": set(),
            "flow_count": 0,
            "attack_flow_count": 0,
        }
    )
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
            raise ValueError(f"CSV has no header: {flow_csv}")

        timestamp_index = find_column_index(header, "Timestamp")
        label_index = find_column_index(header, "Label")

        print(f"Timestamp column index: {timestamp_index}")
        print(f"Label column index: {label_index}")
        print(f"Header columns: {len(header)}")

        for row in reader:
            counters["rows_seen"] += 1
            if len(row) <= max(timestamp_index, label_index):
                counters["invalid_rows"] += 1
                continue

            try:
                minute = parse_timestamp(row[timestamp_index])
            except ValueError:
                counters["invalid_rows"] += 1
                continue

            label = row[label_index].strip()
            entry = minutes[minute]
            entry["flow_count"] += 1

            if label.upper() == "BENIGN":
                counters["benign_flows"] += 1
            else:
                counters["attack_flows"] += 1
                entry["label"] = 1
                entry["attack_flow_count"] += 1
                if label:
                    entry["attack_types"].add(label)

    output_rows: list[dict] = []
    for minute in sorted(minutes):
        entry = minutes[minute]
        output_rows.append({
            "minute_start": minute.strftime("%Y-%m-%d %H:%M:00"),
            "label": entry["label"],
            "attack_types": ";".join(sorted(entry["attack_types"])),
            "flow_count": entry["flow_count"],
            "attack_flow_count": entry["attack_flow_count"],
        })

    counters["minutes"] = len(output_rows)
    counters["attack_minutes"] = sum(row["label"] == 1 for row in output_rows)
    counters["benign_minutes"] = sum(row["label"] == 0 for row in output_rows)
    return output_rows, counters


def write_label_map(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "minute_start",
        "label",
        "attack_types",
        "flow_count",
        "attack_flow_count",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--flow-csv",
        type=Path,
        default=DEFAULT_FLOW_CSV,
        help=f"Input flow-label CSV; default: {DEFAULT_FLOW_CSV}",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output label map; default: {DEFAULT_OUTPUT}",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.flow_csv.is_file():
        raise FileNotFoundError(f"Flow-label CSV does not exist: {args.flow_csv}")

    print(f"Reading flow-label CSV: {args.flow_csv}")
    rows, counters = build_label_map(args.flow_csv)
    write_label_map(rows, args.output)

    print("\nLabel-map summary:")
    for key in (
        "rows_seen",
        "invalid_rows",
        "benign_flows",
        "attack_flows",
        "minutes",
        "benign_minutes",
        "attack_minutes",
    ):
        print(f"  {key}: {counters[key]}")
    print(f"\nWrote: {args.output}")
    print("Existing files and datasets were not modified.")


if __name__ == "__main__":
    main()
