"""Train and evaluate a separate flow-identity-labeled v3 candidate model.

The existing sentinel_model.pkl and integration files are never modified. The
script selects an operating threshold on a chronological validation slice of
the v3 training data, refits on all v3 training data, evaluates once on the
held-out v3 test data, and saves a separate candidate model plus metrics.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    matthews_corrcoef,
    precision_recall_curve,
    roc_auc_score,
)

from feature_pipeline_v2 import model_feature_columns


TRAIN_PATH = Path("..") / "datasets" / "CICIDS2017" / "fast_flow_labeled_v3" / "pcap_flow_labeled_v3_train.csv"
TEST_PATH = Path("..") / "datasets" / "CICIDS2017" / "fast_flow_labeled_v3" / "pcap_flow_labeled_v3_test.csv"
MODEL_PATH = Path("models") / "sentinel_model_v3_candidate.pkl"
METRICS_PATH = Path("models") / "sentinel_model_v3_candidate_metrics.json"
HISTORY_WINDOWS = 5
VALIDATION_FRACTION = 0.20


def make_model() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=500,
        max_depth=30,
        min_samples_split=5,
        class_weight={0: 1, 1: 4},
        random_state=42,
        n_jobs=-1,
    )


def metrics_at_threshold(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predictions, labels=[0, 1]).ravel()
    report = classification_report(
        y_true,
        predictions,
        labels=[0, 1],
        target_names=["BENIGN", "ATTACK"],
        output_dict=True,
        zero_division=0,
    )
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
        "attack_precision": float(report["ATTACK"]["precision"]),
        "attack_recall": float(report["ATTACK"]["recall"]),
        "attack_f1": float(report["ATTACK"]["f1-score"]),
        "benign_precision": float(report["BENIGN"]["precision"]),
        "benign_recall": float(report["BENIGN"]["recall"]),
        "benign_f1": float(report["BENIGN"]["f1-score"]),
        "false_positive_rate": float(fp / max(tn + fp, 1)),
        "false_negative_rate": float(fn / max(fn + tp, 1)),
        "mcc": float(matthews_corrcoef(y_true, predictions)),
        "true_negative": int(tn),
        "false_positive": int(fp),
        "false_negative": int(fn),
        "true_positive": int(tp),
    }


def validate_frame(frame: pd.DataFrame, name: str, feature_columns: list[str]) -> None:
    missing_columns = [column for column in feature_columns + ["label"] if column not in frame.columns]
    if missing_columns:
        raise ValueError(f"{name} is missing columns: {missing_columns}")
    numeric = frame[feature_columns]
    if numeric.isna().any().any():
        raise ValueError(f"{name} contains missing feature values")
    if np.isinf(numeric.to_numpy(dtype=float)).any():
        raise ValueError(f"{name} contains infinite feature values")
    if frame["label"].nunique() < 2:
        raise ValueError(f"{name} contains fewer than two classes")


def select_threshold(y_true: np.ndarray, probabilities: np.ndarray) -> tuple[float, list[dict]]:
    thresholds = np.round(np.arange(0.10, 0.91, 0.05), 2)
    table = [metrics_at_threshold(y_true, probabilities, float(threshold)) for threshold in thresholds]
    best = max(
        table,
        key=lambda item: (
            item["attack_f1"],
            item["attack_recall"],
            -item["false_positive_rate"],
        ),
    )
    return float(best["threshold"]), table


def main() -> None:
    if not TRAIN_PATH.is_file():
        raise FileNotFoundError(TRAIN_PATH)
    if not TEST_PATH.is_file():
        raise FileNotFoundError(TEST_PATH)

    feature_columns = model_feature_columns(HISTORY_WINDOWS)
    train = pd.read_csv(TRAIN_PATH)
    test = pd.read_csv(TEST_PATH)
    validate_frame(train, "v3 train", feature_columns)
    validate_frame(test, "v3 test", feature_columns)

    validation_count = max(1, int(round(len(train) * VALIDATION_FRACTION)))
    fit = train.iloc[:-validation_count].copy()
    validation = train.iloc[-validation_count:].copy()

    X_fit = fit[feature_columns]
    y_fit = fit["label"].to_numpy(dtype=int)
    X_validation = validation[feature_columns]
    y_validation = validation["label"].to_numpy(dtype=int)
    X_train = train[feature_columns]
    y_train = train["label"].to_numpy(dtype=int)
    X_test = test[feature_columns]
    y_test = test["label"].to_numpy(dtype=int)

    print(f"Train rows: {len(train)} | labels: {train['label'].value_counts().to_dict()}")
    print(f"Validation rows: {len(validation)} | labels: {validation['label'].value_counts().to_dict()}")
    print(f"Test rows: {len(test)} | labels: {test['label'].value_counts().to_dict()}")
    print(f"Features: {len(feature_columns)}")

    validation_model = make_model()
    print("Training temporary validation model...")
    validation_model.fit(X_fit, y_fit)
    validation_probabilities = validation_model.predict_proba(X_validation)[:, 1]
    threshold, threshold_table = select_threshold(y_validation, validation_probabilities)
    selected_validation_metrics = metrics_at_threshold(
        y_validation,
        validation_probabilities,
        threshold,
    )
    print(f"Selected threshold from validation: {threshold:.2f}")
    print(f"Validation attack F1: {selected_validation_metrics['attack_f1']:.4f}")

    final_model = make_model()
    print("Training final v3 candidate on all v3 training rows...")
    final_model.fit(X_train, y_train)
    test_probabilities = final_model.predict_proba(X_test)[:, 1]
    test_metrics = metrics_at_threshold(y_test, test_probabilities, threshold)
    test_metrics["roc_auc"] = float(roc_auc_score(y_test, test_probabilities))
    test_metrics["pr_auc"] = float(average_precision_score(y_test, test_probabilities))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open("wb") as handle:
        pickle.dump(final_model, handle, protocol=pickle.HIGHEST_PROTOCOL)

    metrics_payload = {
        "model": "RandomForestClassifier",
        "model_path": str(MODEL_PATH),
        "train_path": str(TRAIN_PATH),
        "test_path": str(TEST_PATH),
        "feature_columns": feature_columns,
        "threshold_selected_on": "chronological_validation_slice",
        "selected_threshold": threshold,
        "validation_metrics": selected_validation_metrics,
        "test_metrics": test_metrics,
        "validation_threshold_table": threshold_table,
        "train_label_counts": {str(k): int(v) for k, v in train["label"].value_counts().to_dict().items()},
        "validation_label_counts": {str(k): int(v) for k, v in validation["label"].value_counts().to_dict().items()},
        "test_label_counts": {str(k): int(v) for k, v in test["label"].value_counts().to_dict().items()},
        "confusion_matrix_labels": ["BENIGN", "ATTACK"],
    }
    with METRICS_PATH.open("w", encoding="utf-8") as handle:
        json.dump(metrics_payload, handle, indent=2)

    print("\nFinal v3 test metrics:")
    for key in (
        "threshold",
        "accuracy",
        "balanced_accuracy",
        "attack_precision",
        "attack_recall",
        "attack_f1",
        "benign_recall",
        "false_positive_rate",
        "false_negative_rate",
        "mcc",
        "roc_auc",
        "pr_auc",
        "true_negative",
        "false_positive",
        "false_negative",
        "true_positive",
    ):
        print(f"  {key}: {test_metrics[key]}")
    print(f"\nSaved candidate model: {MODEL_PATH}")
    print(f"Saved candidate metrics: {METRICS_PATH}")
    print("Existing deployed model and integration files were not modified.")


if __name__ == "__main__":
    main()
