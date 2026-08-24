"""Stratified v3 benchmark across benign and all observed attack families.

Read the complete flow-identity-labeled v3 dataset, remove exact duplicate
feature vectors and contradictory feature/label conflicts, create a stratified
train/validation/test split, select the threshold on validation only, evaluate
once on the stratified test split, and save a separate candidate model. Existing
models and datasets are not modified.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, balanced_accuracy_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import StratifiedShuffleSplit

from feature_pipeline_v2 import model_feature_columns


DATA_PATH = Path("..") / "datasets" / "CICIDS2017" / "fast_flow_labeled_v3" / "pcap_flow_labeled_v3_all.csv"
MODEL_PATH = Path("models") / "sentinel_model_v3_stratified_candidate.pkl"
METRICS_PATH = Path("models") / "sentinel_model_v3_stratified_metrics.json"
HISTORY_WINDOWS = 5
RANDOM_STATE = 42

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


def make_model() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=500,
        max_depth=30,
        min_samples_split=5,
        class_weight={0: 1, 1: 4},
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def stratification_key(frame: pd.DataFrame) -> pd.Series:
    keys = []
    for label, attack_types in zip(frame["label"], frame["attack_types"].fillna("")):
        if int(label) == 0:
            keys.append("BENIGN")
        else:
            values = sorted(item for item in str(attack_types).split(";") if item)
            keys.append(values[0] if values else "ATTACK_UNKNOWN")
    return pd.Series(keys, index=frame.index)


def split_indices(frame: pd.DataFrame, strata: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    first = StratifiedShuffleSplit(n_splits=1, test_size=0.20, random_state=RANDOM_STATE)
    train_val_positions, test_positions = next(first.split(frame, strata))
    train_val_strata = strata.iloc[train_val_positions]
    second = StratifiedShuffleSplit(n_splits=1, test_size=0.25, random_state=RANDOM_STATE)
    train_positions_relative, validation_positions_relative = next(
        second.split(frame.iloc[train_val_positions], train_val_strata)
    )
    train_positions = train_val_positions[train_positions_relative]
    validation_positions = train_val_positions[validation_positions_relative]
    return train_positions, validation_positions, test_positions


def metrics_at_threshold(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    return {
        "threshold": float(threshold),
        "accuracy": float((tn + tp) / max(tn + fp + fn + tp, 1)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
        "attack_precision": float(precision),
        "attack_recall": float(recall),
        "attack_f1": float(f1),
        "false_positive_rate": float(fp / max(tn + fp, 1)),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }


def choose_threshold(y_true: np.ndarray, probabilities: np.ndarray) -> tuple[float, list[dict]]:
    values = []
    for threshold in np.round(np.arange(0.10, 0.91, 0.05), 2):
        values.append(metrics_at_threshold(y_true, probabilities, float(threshold)))
    selected = max(values, key=lambda item: (item["attack_f1"], item["attack_recall"], -item["false_positive_rate"]))
    return float(selected["threshold"]), values


def type_recall(frame: pd.DataFrame, probabilities: np.ndarray, threshold: float) -> dict:
    predictions = probabilities >= threshold
    results: dict[str, dict] = {}
    for attack_type in sorted({
        item
        for value in frame.loc[frame["label"] == 1, "attack_types"].fillna("")
        for item in str(value).split(";")
        if item
    }):
        mask = frame["attack_types"].fillna("").map(lambda value: attack_type in str(value).split(";"))
        count = int(mask.sum())
        detected = int(predictions[mask.to_numpy()].sum())
        results[attack_type] = {
            "windows": count,
            "detected": detected,
            "recall": float(detected / max(count, 1)),
        }
    return results


def main() -> None:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(DATA_PATH)
    data = pd.read_csv(DATA_PATH)
    feature_columns = [column for column in data.columns if column not in METADATA_COLUMNS]
    if data[feature_columns].isna().any().any():
        raise ValueError("The v3 dataset contains missing feature values")
    if np.isinf(data[feature_columns].to_numpy(dtype=float)).any():
        raise ValueError("The v3 dataset contains infinite feature values")

    grouped = data.groupby(feature_columns, dropna=False, sort=False)["label"].nunique()
    conflict_keys = grouped[grouped > 1].index
    conflict_mask = data.set_index(feature_columns).index.isin(conflict_keys)
    conflicting_rows = int(conflict_mask.sum())
    if conflicting_rows:
        data = data.loc[~conflict_mask].copy()
    before_dedup = len(data)
    data = data.drop_duplicates(subset=feature_columns, keep="first").reset_index(drop=True)
    duplicate_rows_removed = before_dedup - len(data)

    strata = stratification_key(data)
    train_positions, validation_positions, test_positions = split_indices(data, strata)
    train = data.iloc[train_positions].copy()
    validation = data.iloc[validation_positions].copy()
    test = data.iloc[test_positions].copy()

    print(f"Rows loaded: {before_dedup + duplicate_rows_removed}")
    print(f"Contradictory feature/label rows removed: {conflicting_rows}")
    print(f"Exact duplicate feature rows removed: {duplicate_rows_removed}")
    print(f"Rows benchmarked: {len(data)}")
    for name, frame in (("TRAIN", train), ("VALIDATION", validation), ("TEST", test)):
        print(f"{name}: rows={len(frame)} labels={frame['label'].value_counts().to_dict()} strata={stratification_key(frame).value_counts().to_dict()}")

    X_train = train[feature_columns]
    y_train = train["label"].to_numpy(dtype=int)
    X_validation = validation[feature_columns]
    y_validation = validation["label"].to_numpy(dtype=int)
    X_test = test[feature_columns]
    y_test = test["label"].to_numpy(dtype=int)

    validation_model = make_model()
    print("Training validation model...")
    validation_model.fit(X_train, y_train)
    validation_probabilities = validation_model.predict_proba(X_validation)[:, 1]
    threshold, validation_table = choose_threshold(y_validation, validation_probabilities)
    validation_metrics = metrics_at_threshold(y_validation, validation_probabilities, threshold)
    print(f"Validation-selected threshold: {threshold:.2f} | attack F1={validation_metrics['attack_f1']:.4f}")

    final_model = make_model()
    print("Training final stratified candidate...")
    final_model.fit(X_train, y_train)
    test_probabilities = final_model.predict_proba(X_test)[:, 1]
    test_metrics = metrics_at_threshold(y_test, test_probabilities, threshold)
    test_metrics["roc_auc"] = float(roc_auc_score(y_test, test_probabilities))
    test_metrics["pr_auc"] = float(average_precision_score(y_test, test_probabilities))
    per_type = type_recall(test, test_probabilities, threshold)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open("wb") as handle:
        pickle.dump(final_model, handle, protocol=pickle.HIGHEST_PROTOCOL)
    payload = {
        "data_path": str(DATA_PATH),
        "model_path": str(MODEL_PATH),
        "feature_count": len(feature_columns),
        "conflicting_rows_removed": conflicting_rows,
        "duplicate_feature_rows_removed": duplicate_rows_removed,
        "rows_benchmarked": len(data),
        "split_sizes": {"train": len(train), "validation": len(validation), "test": len(test)},
        "split_label_counts": {
            name: {str(k): int(v) for k, v in frame["label"].value_counts().to_dict().items()}
            for name, frame in (("train", train), ("validation", validation), ("test", test))
        },
        "selected_threshold": threshold,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "test_attack_type_recall": per_type,
        "validation_threshold_table": validation_table,
    }
    with METRICS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print("\nSTRATIFIED TEST METRICS")
    for key, value in test_metrics.items():
        print(f"  {key}: {value}")
    print("PER-ATTACK-TYPE RECALL")
    for attack_type, values in per_type.items():
        print(f"  {attack_type}: {values}")
    print(f"Saved separate model: {MODEL_PATH}")
    print(f"Saved separate metrics: {METRICS_PATH}")
    print("Existing models, datasets, and integration files were not modified.")


if __name__ == "__main__":
    main()
