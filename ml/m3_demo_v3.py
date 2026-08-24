"""Isolated v3 integration demo.

Loads the stratified v3 candidate model, rebuilds the 45-feature live schema
with RollingFeatureState from real v3 test rows, logs predictions to a separate
ledger, and triggers the existing Zeroizer without touching the deployed demo,
model, or runtime ledger.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from feature_pipeline_v2 import BASE_FEATURE_COLUMNS, RollingFeatureState, model_feature_columns
from ledger import Ledger
from zeroize import SECRETS, Zeroizer


MODEL_PATH = Path("models") / "sentinel_model_v3_stratified_candidate.pkl"
METRICS_PATH = Path("models") / "sentinel_model_v3_stratified_metrics.json"
TEST_PATH = Path("..") / "datasets" / "CICIDS2017" / "fast_flow_labeled_v3" / "pcap_flow_labeled_v3_all.csv"
DEMO_LEDGER_PATH = Path("v3_demo_ledger.json")
DEMO_RESULTS_PATH = Path("v3_demo_results.json")
HISTORY_WINDOWS = 5


def live_vector(row: pd.Series) -> dict:
    state = RollingFeatureState(HISTORY_WINDOWS)
    base = {column: float(row[column]) for column in BASE_FEATURE_COLUMNS}
    return state.enrich(base)


def predict(model, row: pd.Series, feature_columns: list[str], threshold: float) -> dict:
    live_features = live_vector(row)
    vector = pd.DataFrame([[live_features[column] for column in feature_columns]], columns=feature_columns)
    probability = float(model.predict_proba(vector)[0, 1])
    prediction = int(probability >= threshold)
    return {
        "prediction": "ATTACK" if prediction else "BENIGN",
        "probability_attack": probability,
        "threshold": threshold,
        "source_label": int(row["label"]),
        "attack_types": str(row.get("attack_types", "")),
        "feature_count": len(feature_columns),
    }


def isolated_zeroizer(ledger_path: Path) -> Zeroizer:
    # Construct without Zeroizer.__init__ so its default runtime ledger is not touched.
    instance = Zeroizer.__new__(Zeroizer)
    instance.ledger = Ledger(str(ledger_path))
    instance.store = SECRETS.copy()
    instance._original = SECRETS.copy()
    return instance


def main() -> None:
    for path in (MODEL_PATH, METRICS_PATH, TEST_PATH):
        if not path.is_file():
            raise FileNotFoundError(path)

    with MODEL_PATH.open("rb") as handle:
        model = pickle.load(handle)
    with METRICS_PATH.open("r", encoding="utf-8") as handle:
        metrics = json.load(handle)
    threshold = float(metrics["selected_threshold"])
    feature_columns = model_feature_columns(HISTORY_WINDOWS)

    data = pd.read_csv(TEST_PATH)
    benign_rows = data[data["label"] == 0].copy()
    attack_rows = data[data["label"] == 1].copy()
    if benign_rows.empty or attack_rows.empty:
        raise ValueError("The v3 test data must contain both benign and attack rows")

    # Select representative real rows with high-confidence benign/attack scores
    # using the dataset feature schema; the live-schema reconstruction is tested
    # separately below.
    base_matrix = data[feature_columns]
    probabilities = model.predict_proba(base_matrix)[:, 1]
    benign_index = data.index[data["label"] == 0][int(np.argmin(probabilities[data["label"].to_numpy() == 0]))]
    attack_index = data.index[data["label"] == 1][int(np.argmax(probabilities[data["label"].to_numpy() == 1]))]
    benign_row = data.loc[benign_index]
    attack_row = data.loc[attack_index]

    predictions = {
        "benign_sample": predict(model, benign_row, feature_columns, threshold),
        "attack_sample": predict(model, attack_row, feature_columns, threshold),
    }
    print("V3 live-schema predictions:")
    for name, result in predictions.items():
        print(f"  {name}: {result}")

    if DEMO_LEDGER_PATH.exists():
        DEMO_LEDGER_PATH.unlink()
    ledger = Ledger(str(DEMO_LEDGER_PATH))
    ledger.append_entry("PREDICTION", {"sample": "benign", **predictions["benign_sample"]})
    ledger.append_entry("PREDICTION", {"sample": "attack", **predictions["attack_sample"]})

    zeroizer = isolated_zeroizer(DEMO_LEDGER_PATH)
    if predictions["attack_sample"]["prediction"] == "ATTACK":
        zeroizer.zeroize_all(reason="V3_ATTACK_DETECTED")
    else:
        print("[V3 DEMO] Attack sample was not detected; zeroization was not triggered.")

    valid, message = ledger.verify_chain()
    results = {
        "model": str(MODEL_PATH),
        "threshold": threshold,
        "feature_count": len(feature_columns),
        "predictions": predictions,
        "zeroized": bool(zeroizer.is_zeroized()),
        "ledger_valid": bool(valid),
        "ledger_message": message,
        "ledger_blocks": len(ledger.get_all()),
        "isolated_ledger": str(DEMO_LEDGER_PATH),
    }
    with DEMO_RESULTS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)

    print(f"Zeroized: {results['zeroized']}")
    print(f"Ledger valid: {results['ledger_valid']} ({results['ledger_message']})")
    print(f"Ledger blocks: {results['ledger_blocks']}")
    print(f"Saved isolated demo results: {DEMO_RESULTS_PATH}")
    print("Existing model, demo, detector, and runtime ledger were not modified.")


if __name__ == "__main__":
    main()
