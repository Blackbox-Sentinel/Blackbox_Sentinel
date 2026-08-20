"""Validate the adaptive baseline on real flow-labeled v3 windows.

The label is used only for evaluation.  The baseline itself is trained from
benign rows and never receives the evaluation labels.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from adaptive_baseline import AdaptiveBaseline
from feature_pipeline_v2 import model_feature_columns


DEFAULT_DATASET = (
    Path("..")
    / "datasets"
    / "CICIDS2017"
    / "fast_flow_labeled_v3"
    / "pcap_flow_labeled_v3_all.csv"
)


def evaluate(profile: AdaptiveBaseline, frame: pd.DataFrame) -> dict:
    results = []
    for _, row in frame.iterrows():
        features = {column: float(row[column]) for column in profile.feature_columns}
        results.append(profile.score(features))
    if not results:
        return {"samples": 0, "anomalies": 0, "anomaly_rate": 0.0}
    anomalies = sum(int(result["local_anomaly"]) for result in results)
    return {
        "samples": len(results),
        "anomalies": anomalies,
        "anomaly_rate": anomalies / len(results),
        "mean_local_score": sum(result["local_score"] for result in results)
        / len(results),
        "mean_max_robust_z": sum(result["max_robust_z"] for result in results)
        / len(results),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--baseline-size", type=int, default=1_000)
    parser.add_argument("--evaluation-size", type=int, default=500)
    parser.add_argument("--output", type=Path, default=Path("adaptive_baseline_validation.json"))
    args = parser.parse_args()

    if args.baseline_size < 32 or args.evaluation_size < 1:
        raise ValueError("baseline-size must be >= 32 and evaluation-size must be positive")

    frame = pd.read_csv(args.dataset)
    feature_columns = model_feature_columns(5)
    benign = frame[frame["label"] == 0].copy()
    attacks = frame[frame["label"] == 1].copy()
    if len(benign) < args.baseline_size + args.evaluation_size:
        raise ValueError("Not enough benign rows for requested validation")
    if len(attacks) < args.evaluation_size:
        raise ValueError("Not enough attack rows for requested validation")

    profile = AdaptiveBaseline(
        feature_columns=feature_columns,
        organization_id="real_v3_validation",
        min_baseline_samples=args.baseline_size,
        reservoir_size=min(2_048, args.baseline_size),
    )
    baseline = benign.iloc[: args.baseline_size]
    for _, row in baseline.iterrows():
        profile.observe({column: float(row[column]) for column in feature_columns})

    benign_eval = benign.iloc[args.baseline_size : args.baseline_size + args.evaluation_size]
    attack_eval = attacks.iloc[: args.evaluation_size]
    output = {
        "dataset": str(args.dataset),
        "baseline": profile.summary(),
        "benign_evaluation": evaluate(profile, benign_eval),
        "attack_evaluation": evaluate(profile, attack_eval),
        "attack_types": attack_eval.get("attack_types", pd.Series(dtype=str)).value_counts().to_dict(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
