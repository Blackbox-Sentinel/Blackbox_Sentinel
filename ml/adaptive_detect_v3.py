"""Organization-specific adaptive detector built around the validated v3 model.

This file is intentionally isolated from detect.py, m3_demo.py, feature_extract.py,
ledger.py, zeroize.py, and the deployed model.  It combines:

1. the frozen v3 Random Forest for known attack patterns; and
2. a per-organization robust baseline that learns only trusted normal windows.

The live mode is bounded by --duration-seconds and can be run for a two-day
baseline.  No raw packets or IP addresses are persisted by this module; only
aggregated feature windows, predictions, and a local profile are stored.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pickle
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from adaptive_baseline import AdaptiveBaseline
from feature_pipeline_v2 import (
    RollingFeatureState,
    capture_live_window,
    model_feature_columns,
)


MODEL_PATH = Path("models") / "sentinel_model_v3_stratified_candidate.pkl"
METRICS_PATH = Path("models") / "sentinel_model_v3_stratified_metrics.json"
HISTORY_WINDOWS = 5
DEFAULT_ORGANIZATION = "default_organization"
DEFAULT_DURATION_SECONDS = 172_800.0
DEFAULT_PROFILE_ROOT = Path("adaptive_profiles")


class AppendOnlyEventLog:
    """Small append-only hash chain suitable for long-running monitoring."""

    def __init__(self, path: Path, reset: bool = False) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if reset and self.path.exists():
            self.path.unlink()
        self.previous_hash = "0" * 64
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.previous_hash = json.loads(line)["hash"]

    def append(self, event: str, data: Mapping) -> dict:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "data": dict(data),
            "previous_hash": self.previous_hash,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        record = {**payload, "hash": digest}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.previous_hash = digest
        return record

    def verify(self) -> tuple[bool, str, int]:
        previous_hash = "0" * 64
        count = 0
        if not self.path.exists():
            return True, "Empty event log", 0
        for line_number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            record = json.loads(line)
            expected_payload = {
                "timestamp": record["timestamp"],
                "event": record["event"],
                "data": record["data"],
                "previous_hash": record["previous_hash"],
            }
            expected_hash = hashlib.sha256(
                json.dumps(
                    expected_payload, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            if record["previous_hash"] != previous_hash:
                return False, f"Previous hash mismatch at line {line_number}", count
            if record["hash"] != expected_hash:
                return False, f"Hash mismatch at line {line_number}", count
            previous_hash = record["hash"]
            count += 1
        return True, "Chain valid", count


def safe_organization_name(value: str) -> str:
    cleaned = "".join(
        character if character.isalnum() or character in ("-", "_") else "_"
        for character in value.strip()
    )
    if not cleaned:
        raise ValueError("organization-id must contain at least one valid character")
    return cleaned[:120]


def load_model_and_threshold():
    with MODEL_PATH.open("rb") as handle:
        model = pickle.load(handle)
    with METRICS_PATH.open("r", encoding="utf-8") as handle:
        metrics = json.load(handle)
    return model, float(metrics["selected_threshold"])


def model_probability(model, feature_row: Mapping[str, float], columns: list[str]) -> float:
    vector = pd.DataFrame(
        [[float(feature_row[column]) for column in columns]], columns=columns
    )
    return float(model.predict_proba(vector)[0, 1])


def classify_window(
    model,
    feature_row: Mapping[str, float],
    columns: list[str],
    profile: AdaptiveBaseline,
    threshold: float,
    baseline_accept_probability: float,
    min_outlier_features: int,
    local_detection_enabled: bool = True,
) -> dict:
    probability = model_probability(model, feature_row, columns)
    local = profile.score(
        feature_row,
        min_outlier_features=min_outlier_features,
    )
    global_attack = probability >= threshold
    local_attack = bool(local["local_anomaly"])

    # A window is eligible to teach the profile only when the frozen model is
    # confident it is benign and the local profile does not call it unusual.
    # During warm-up the local score is not ready, so the global confidence gate
    # remains the protection against poisoning the initial baseline.
    eligible_for_learning = (
        probability <= baseline_accept_probability and not local_attack
    )
    if eligible_for_learning:
        profile.observe(feature_row)
    else:
        profile.reject()

    combined_attack = bool(
        global_attack or (local_detection_enabled and local_attack)
    )
    return {
        "timestamp": str(feature_row.get("timestamp", "")),
        "probability_attack": probability,
        "global_prediction": "ATTACK" if global_attack else "BENIGN",
        "local_prediction": (
            ("ANOMALY" if local_attack else "NORMAL")
            if local_detection_enabled
            else "LEARNING"
        ),
        "combined_prediction": "ATTACK" if combined_attack else "BENIGN",
        "local_detection_enabled": local_detection_enabled,
        "threshold": threshold,
        "baseline_accept_probability": baseline_accept_probability,
        "eligible_for_learning": eligible_for_learning,
        "profile_ready": bool(local["ready"]),
        "profile_samples": int(profile.accepted_samples),
        "local_score": float(local["local_score"]),
        "max_robust_z": float(local["max_robust_z"]),
        "outlier_feature_count": int(local["outlier_feature_count"]),
        "top_local_features": list(local.get("top_features", [])),
        "feature_count": len(columns),
    }


def append_feature_row(
    path: Path,
    feature_row: Mapping[str, float],
    result: Mapping,
    columns: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = columns + [
        "detector_timestamp",
        "probability_attack",
        "global_prediction",
        "local_prediction",
        "combined_prediction",
        "profile_ready",
        "eligible_for_learning",
    ]
    new_file = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if new_file:
            writer.writeheader()
        row = {column: float(feature_row[column]) for column in columns}
        row.update(
            {
                "detector_timestamp": result["timestamp"],
                "probability_attack": result["probability_attack"],
                "global_prediction": result["global_prediction"],
                "local_prediction": result["local_prediction"],
                "combined_prediction": result["combined_prediction"],
                "profile_ready": result["profile_ready"],
                "eligible_for_learning": result["eligible_for_learning"],
            }
        )
        writer.writerow(row)


def fixture_rows(path: Path, max_samples: int) -> Iterable[dict]:
    frame = pd.read_csv(path)
    if frame.empty:
        raise ValueError("Fixture CSV is empty")
    for _, row in frame.iloc[:max_samples].iterrows():
        yield row.to_dict()


def feature_row_from_fixture(row: Mapping[str, object], columns: list[str]) -> dict:
    return {
        column: float(row[column])
        for column in columns
    } | {
        "timestamp": str(row.get("timestamp", "")),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run an isolated per-organization adaptive v3 detector"
    )
    parser.add_argument("--organization-id", default=DEFAULT_ORGANIZATION)
    parser.add_argument("--fixture-csv", type=Path)
    parser.add_argument("--iface", default=None)
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument(
        "--duration-seconds",
        type=float,
        default=0.0,
        help="Total run time; 0 means run until stopped",
    )
    parser.add_argument(
        "--baseline-duration-seconds",
        type=float,
        default=DEFAULT_DURATION_SECONDS,
        help="Time to learn this organization before local alerts activate",
    )
    parser.add_argument("--max-samples", type=int)
    parser.add_argument("--min-baseline-samples", type=int, default=2_048)
    parser.add_argument("--reservoir-size", type=int, default=2_048)
    parser.add_argument("--baseline-accept-probability", type=float, default=0.25)
    parser.add_argument("--min-outlier-features", type=int, default=3)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--event-log", type=Path)
    parser.add_argument("--feature-log", type=Path)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--save-every", type=int, default=60)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.duration_seconds < 0 or args.baseline_duration_seconds < 0:
        raise ValueError("run durations must be non-negative")
    if not 0 < args.baseline_accept_probability < 1:
        raise ValueError("baseline-accept-probability must be between 0 and 1")
    if args.save_every < 1:
        raise ValueError("save-every must be positive")
    if not MODEL_PATH.is_file() or not METRICS_PATH.is_file():
        raise FileNotFoundError("v3 model or metrics file is missing")

    model, threshold = load_model_and_threshold()
    feature_columns = model_feature_columns(HISTORY_WINDOWS)
    organization_name = safe_organization_name(args.organization_id)
    args.organization_id = organization_name
    profile_path = args.profile or (
        DEFAULT_PROFILE_ROOT / f"{organization_name}_profile.json"
    )
    event_log_path = args.event_log or (
        DEFAULT_PROFILE_ROOT / f"{organization_name}_events.jsonl"
    )
    feature_log_path = args.feature_log or (
        DEFAULT_PROFILE_ROOT / f"{organization_name}_features.csv"
    )
    profile = AdaptiveBaseline.load_or_create(
        profile_path,
        feature_columns=feature_columns,
        organization_id=args.organization_id,
        min_baseline_samples=args.min_baseline_samples,
        reservoir_size=args.reservoir_size,
    )
    event_log = AppendOnlyEventLog(event_log_path, reset=args.reset)
    state = RollingFeatureState(HISTORY_WINDOWS)

    event_log.append(
        "RUN_STARTED",
        {
            "organization_id": args.organization_id,
            "mode": "fixture" if args.fixture_csv else "live_capture",
            "duration_seconds": args.duration_seconds,
            "baseline_duration_seconds": args.baseline_duration_seconds,
            "model": str(MODEL_PATH),
            "threshold": threshold,
            "feature_count": len(feature_columns),
            "profile_ready": profile.ready,
        },
    )

    start = time.monotonic()
    sample_index = 0
    global_attacks = 0
    local_anomalies = 0
    combined_attacks = 0
    learning_accepts = 0
    learning_rejects = 0

    if args.fixture_csv:
        max_samples = args.max_samples or 2
        rows = fixture_rows(args.fixture_csv, max_samples)
        source_iterator = (
            feature_row_from_fixture(row, feature_columns) for row in rows
        )
    else:
        source_iterator = None

    while True:
        if args.max_samples is not None and sample_index >= args.max_samples:
            break
        elapsed_seconds = (
            sample_index * args.timeout
            if source_iterator is not None
            else time.monotonic() - start
        )
        if args.duration_seconds and elapsed_seconds >= args.duration_seconds:
            break
        local_detection_enabled = (
            elapsed_seconds >= args.baseline_duration_seconds and profile.ready
        )

        if source_iterator is not None:
            try:
                raw_row = next(source_iterator)
            except StopIteration:
                break
            feature_row = state.enrich(
                {column: raw_row[column] for column in feature_columns}
            )
            feature_row["timestamp"] = raw_row.get("timestamp", "")
        else:
            feature_row = capture_live_window(
                timeout=args.timeout,
                iface=args.iface,
                history_state=state,
            )

        result = classify_window(
            model,
            feature_row,
            feature_columns,
            profile,
            threshold,
            args.baseline_accept_probability,
            args.min_outlier_features,
            local_detection_enabled=local_detection_enabled,
        )
        sample_index += 1
        global_attacks += int(result["global_prediction"] == "ATTACK")
        local_anomalies += int(
            result["local_detection_enabled"] and result["local_prediction"] == "ANOMALY"
        )
        combined_attacks += int(result["combined_prediction"] == "ATTACK")
        learning_accepts += int(result["eligible_for_learning"])
        learning_rejects += int(not result["eligible_for_learning"])
        append_feature_row(feature_log_path, feature_row, result, feature_columns)

        if result["combined_prediction"] == "ATTACK":
            event_log.append(
                "ALERT",
                {
                    "sample_index": sample_index,
                    "organization_id": args.organization_id,
                    **result,
                },
            )
        elif sample_index % args.save_every == 0:
            event_log.append(
                "HEARTBEAT",
                {
                    "sample_index": sample_index,
                    "organization_id": args.organization_id,
                    "profile_ready": profile.ready,
                    "local_detection_enabled": local_detection_enabled,
                    "profile_samples": profile.accepted_samples,
                },
            )

        if sample_index % args.save_every == 0:
            profile.save(profile_path)

        if source_iterator is None:
            # sniff(timeout=1) already consumes almost all of the interval.  A
            # short pause avoids a busy loop when an interface returns early.
            time.sleep(0.05)

    profile.save(profile_path)
    event_log.append(
        "RUN_FINISHED",
        {
            "organization_id": args.organization_id,
            "samples": sample_index,
            "global_attacks": global_attacks,
            "local_anomalies": local_anomalies,
            "combined_attacks": combined_attacks,
            "learning_accepts": learning_accepts,
            "learning_rejects": learning_rejects,
            "baseline_complete": local_detection_enabled,
            "profile": str(profile_path),
            "profile_summary": profile.summary(),
        },
    )
    valid, message, event_count = event_log.verify()
    summary = {
        "organization_id": args.organization_id,
        "mode": "fixture" if args.fixture_csv else "live_capture",
        "samples": sample_index,
        "global_attacks": global_attacks,
        "local_anomalies": local_anomalies,
        "combined_attacks": combined_attacks,
        "learning_accepts": learning_accepts,
        "learning_rejects": learning_rejects,
        "profile_ready": profile.ready,
        "baseline_complete": (
            sample_index * args.timeout >= args.baseline_duration_seconds
            if source_iterator is not None
            else time.monotonic() - start >= args.baseline_duration_seconds
        ),
        "profile": str(profile_path),
        "profile_summary": profile.summary(),
        "event_log": str(event_log_path),
        "event_count": event_count,
        "event_chain_valid": valid,
        "event_chain_message": message,
        "feature_log": str(feature_log_path),
        "model": str(MODEL_PATH),
        "threshold": threshold,
        "feature_count": len(feature_columns),
    }
    summary_path = event_log_path.with_suffix(".summary.json")
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
