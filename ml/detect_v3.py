"""Isolated v3 live detector.

This path uses the 45-feature schema and RollingFeatureState from
feature_pipeline_v2. It supports a fixture mode for safe local testing and a
live Scapy capture mode. It writes only an isolated v3 ledger and results file;
the existing detector, runtime ledger, and deployed model are untouched.
"""

from __future__ import annotations

import argparse
import json
import pickle
import time
from pathlib import Path

import pandas as pd

from feature_pipeline_v2 import BASE_FEATURE_COLUMNS, RollingFeatureState, capture_live_window, model_feature_columns
from ledger import Ledger
from zeroize import SECRETS, Zeroizer


MODEL_PATH = Path("models") / "sentinel_model_v3_stratified_candidate.pkl"
METRICS_PATH = Path("models") / "sentinel_model_v3_stratified_metrics.json"
DEFAULT_LEDGER_PATH = Path("v3_live_ledger.json")
DEFAULT_RESULTS_PATH = Path("v3_live_results.json")
HISTORY_WINDOWS = 5


def isolated_zeroizer(ledger_path: Path) -> Zeroizer:
    instance = Zeroizer.__new__(Zeroizer)
    instance.ledger = Ledger(str(ledger_path))
    instance.store = SECRETS.copy()
    instance._original = SECRETS.copy()
    return instance


def load_model_and_threshold():
    with MODEL_PATH.open("rb") as handle:
        model = pickle.load(handle)
    with METRICS_PATH.open("r", encoding="utf-8") as handle:
        metrics = json.load(handle)
    return model, float(metrics["selected_threshold"])


def fixture_rows(path: Path, max_samples: int) -> list[pd.Series]:
    frame = pd.read_csv(path)
    benign = frame[frame["label"] == 0]
    attack = frame[frame["label"] == 1]
    if benign.empty or attack.empty:
        raise ValueError("Fixture CSV must contain both benign and attack rows")
    rows = [benign.iloc[0], attack.iloc[0]]
    if max_samples > 2:
        rows.extend([row for _, row in frame.iloc[:max_samples].iterrows()])
    return rows[:max_samples]


def fixture_to_feature_row(row: pd.Series, state: RollingFeatureState) -> dict:
    base = {column: float(row[column]) for column in BASE_FEATURE_COLUMNS}
    enriched = state.enrich(base)
    enriched["timestamp"] = str(row.get("timestamp", ""))
    return enriched


def classify(model, feature_row: dict, feature_columns: list[str], threshold: float) -> dict:
    vector = pd.DataFrame([[feature_row[column] for column in feature_columns]], columns=feature_columns)
    probability = float(model.predict_proba(vector)[0, 1])
    prediction = int(probability >= threshold)
    return {
        "prediction": "ATTACK" if prediction else "BENIGN",
        "probability_attack": probability,
        "threshold": threshold,
        "feature_count": len(feature_columns),
        "timestamp": feature_row.get("timestamp", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run isolated v3 live detection")
    parser.add_argument("--fixture-csv", type=Path, help="Use real v3 rows instead of sniffing live traffic")
    parser.add_argument("--iface", default=None, help="Scapy interface for live capture")
    parser.add_argument("--timeout", type=float, default=1.0)
    parser.add_argument("--max-samples", type=int, default=2)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS_PATH)
    args = parser.parse_args()

    for path in (MODEL_PATH, METRICS_PATH):
        if not path.is_file():
            raise FileNotFoundError(path)

    model, threshold = load_model_and_threshold()
    feature_columns = model_feature_columns(HISTORY_WINDOWS)
    state = RollingFeatureState(HISTORY_WINDOWS)
    ledger_path = args.ledger
    if ledger_path.exists():
        ledger_path.unlink()
    ledger = Ledger(str(ledger_path))
    zeroizer = isolated_zeroizer(ledger_path)
    results = []

    if args.fixture_csv:
        rows = fixture_rows(args.fixture_csv, args.max_samples)
        for index, row in enumerate(rows, start=1):
            feature_row = fixture_to_feature_row(row, state)
            result = classify(model, feature_row, feature_columns, threshold)
            result["sample_index"] = index
            result["source_label"] = int(row["label"])
            result["attack_types"] = str(row.get("attack_types", ""))
            results.append(result)
            ledger.append_entry("PREDICTION", result)
            if result["prediction"] == "ATTACK":
                zeroizer.zeroize_all(reason="V3_LIVE_ATTACK_DETECTED")
            print(f"[{index}] {result}")
    else:
        for index in range(1, args.max_samples + 1):
            feature_row = capture_live_window(
                timeout=args.timeout,
                iface=args.iface,
                history_state=state,
            )
            result = classify(model, feature_row, feature_columns, threshold)
            result["sample_index"] = index
            results.append(result)
            ledger.append_entry("PREDICTION", result)
            if result["prediction"] == "ATTACK":
                zeroizer.zeroize_all(reason="V3_LIVE_ATTACK_DETECTED")
            print(f"[{index}] {result}")
            if index < args.max_samples:
                time.sleep(0.1)

    valid, message = ledger.verify_chain()
    payload = {
        "model": str(MODEL_PATH),
        "threshold": threshold,
        "feature_count": len(feature_columns),
        "mode": "fixture" if args.fixture_csv else "live_capture",
        "results": results,
        "zeroized": bool(zeroizer.is_zeroized()),
        "ledger_valid": bool(valid),
        "ledger_message": message,
        "ledger_blocks": len(ledger.get_all()),
        "ledger_path": str(ledger_path),
    }
    with args.results.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print(f"Zeroized: {payload['zeroized']}")
    print(f"Ledger valid: {payload['ledger_valid']} ({payload['ledger_message']})")
    print(f"Ledger blocks: {payload['ledger_blocks']}")
    print(f"Saved isolated results: {args.results}")
    print("Existing detector, runtime ledger, deployed model, and integration files were not modified.")


if __name__ == "__main__":
    main()
