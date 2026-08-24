"""Audit v3 split integrity, metadata leakage, attack types, and thresholds.

This script is read-only. It loads the v3 CSVs and separate candidate model,
prints diagnostics, and writes no files.
"""

from __future__ import annotations

import pickle
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score


DATA_DIR = Path("..") / "datasets" / "CICIDS2017" / "fast_flow_labeled_v3"
TRAIN_PATH = DATA_DIR / "pcap_flow_labeled_v3_train.csv"
TEST_PATH = DATA_DIR / "pcap_flow_labeled_v3_test.csv"
MODEL_PATH = Path("models") / "sentinel_model_v3_candidate.pkl"

METADATA_COLUMNS = {
    "timestamp",
    "window_start_epoch",
    "source_file",
    "label_source",
    "attack_types",
    "matched_packet_count",
    "attack_packet_count",
    "unmatched_packet_count",
    "label",
}
THRESHOLDS = np.round(np.arange(0.10, 0.91, 0.05), 2)


def classification_metrics(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    return {
        "threshold": float(threshold),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fp / max(tn + fp, 1),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def print_split_summary(name: str, frame: pd.DataFrame, feature_columns: list[str]) -> None:
    labels = frame["label"].value_counts().to_dict()
    attack_share = float(frame["label"].mean())
    timestamps = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    print(
        f"{name}: rows={len(frame)} labels={labels} "
        f"attack_share={attack_share:.4f} "
        f"time={timestamps.min()}..{timestamps.max()}"
    )
    print(f"  duplicate full rows: {int(frame.duplicated().sum())}")
    print(f"  duplicate feature rows: {int(frame.duplicated(subset=feature_columns).sum())}")
    print(f"  missing numeric values: {int(frame[feature_columns].isna().sum().sum())}")
    print(f"  infinite numeric values: {int(np.isinf(frame[feature_columns].to_numpy(dtype=float)).sum())}")


def feature_overlap(train: pd.DataFrame, test: pd.DataFrame, feature_columns: list[str]) -> None:
    train_features = train[feature_columns].round(6).to_numpy()
    test_features = test[feature_columns].round(6).to_numpy()
    train_set = set(map(tuple, train_features))
    test_set = set(map(tuple, test_features))
    overlap = train_set.intersection(test_set)
    print(f"Exact rounded feature-vector overlap train/test: {len(overlap)}")
    print(
        "Feature columns containing suspicious label metadata: "
        f"{[c for c in feature_columns if any(word in c.lower() for word in ('label', 'attack', 'match'))]}"
    )


def attack_type_summary(name: str, frame: pd.DataFrame) -> None:
    counter = Counter()
    for value, label in zip(frame["attack_types"].fillna(""), frame["label"]):
        if int(label) != 1:
            continue
        attack_types = [item for item in str(value).split(";") if item]
        if not attack_types:
            counter["ATTACK_WITHOUT_TYPE"] += 1
        else:
            counter.update(attack_types)
    print(f"{name} attack-type windows: {dict(counter)}")


def main() -> None:
    if not TRAIN_PATH.is_file():
        raise FileNotFoundError(TRAIN_PATH)
    if not TEST_PATH.is_file():
        raise FileNotFoundError(TEST_PATH)
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(MODEL_PATH)

    train = pd.read_csv(TRAIN_PATH)
    test = pd.read_csv(TEST_PATH)
    feature_columns = [
        column
        for column in train.columns
        if column not in METADATA_COLUMNS
    ]

    print(f"Feature count used by audit: {len(feature_columns)}")
    print(f"Feature columns: {feature_columns}")
    print_split_summary("TRAIN", train, feature_columns)
    print_split_summary("TEST", test, feature_columns)
    feature_overlap(train, test, feature_columns)
    attack_type_summary("TRAIN", train)
    attack_type_summary("TEST", test)

    train_attack_times = pd.to_datetime(
        train.loc[train["label"] == 1, "timestamp"], errors="coerce", utc=True
    )
    test_attack_times = pd.to_datetime(
        test.loc[test["label"] == 1, "timestamp"], errors="coerce", utc=True
    )
    print(
        f"Attack time range train: {train_attack_times.min()}..{train_attack_times.max()}"
    )
    print(
        f"Attack time range test: {test_attack_times.min()}..{test_attack_times.max()}"
    )

    with MODEL_PATH.open("rb") as handle:
        model = pickle.load(handle)
    probabilities = model.predict_proba(test[feature_columns])[:, 1]
    y_test = test["label"].to_numpy(dtype=int)
    print(f"Candidate model ROC-AUC: {roc_auc_score(y_test, probabilities):.6f}")
    print(f"Candidate model PR-AUC: {average_precision_score(y_test, probabilities):.6f}")
    print("Test threshold table:")
    print("threshold|precision|recall|f1|fpr|tn|fp|fn|tp")
    for threshold in THRESHOLDS:
        metrics = classification_metrics(y_test, probabilities, float(threshold))
        print(
            f"{metrics['threshold']:.2f}|{metrics['precision']:.4f}|"
            f"{metrics['recall']:.4f}|{metrics['f1']:.4f}|{metrics['fpr']:.4f}|"
            f"{metrics['tn']}|{metrics['fp']}|{metrics['fn']}|{metrics['tp']}"
        )

    print("No files were written.")


if __name__ == "__main__":
    main()
