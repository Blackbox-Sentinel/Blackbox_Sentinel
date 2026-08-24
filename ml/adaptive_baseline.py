"""Per-organization adaptive traffic baseline.

This module intentionally does not modify the existing detector or model. It
learns only rows explicitly accepted by the caller and provides an unsupervised
Isolation Forest for multivariate organization-specific anomaly detection. A
robust quantile diagnostic is also retained so alerts can explain which
features are unusual.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Mapping

import numpy as np
from sklearn.ensemble import IsolationForest


class AdaptiveBaseline:
    """Bounded, serializable baseline profile for one organization.

    The profile keeps a bounded row reservoir. During the initial baseline,
    callers should pass only trusted rows. Once enough rows are collected, an
    Isolation Forest is fitted to the organization's multivariate traffic
    shape. The model is periodically refitted from the bounded reservoir so
    the profile can adapt without retaining all network history.
    """

    FORMAT_VERSION = 2

    def __init__(
        self,
        feature_columns: list[str],
        organization_id: str,
        min_baseline_samples: int = 172_800,
        reservoir_size: int = 2_048,
        refit_interval: int = 2_048,
        random_seed: int = 42,
    ) -> None:
        if not feature_columns:
            raise ValueError("feature_columns must not be empty")
        if not organization_id.strip():
            raise ValueError("organization_id must not be empty")
        if min_baseline_samples < 1:
            raise ValueError("min_baseline_samples must be positive")
        if reservoir_size < 32:
            raise ValueError("reservoir_size must be at least 32")
        if refit_interval < 1:
            raise ValueError("refit_interval must be positive")

        self.feature_columns = list(feature_columns)
        self.organization_id = organization_id
        self.min_baseline_samples = int(min_baseline_samples)
        self.reservoir_size = int(reservoir_size)
        self.refit_interval = int(refit_interval)
        self.random_seed = int(random_seed)
        self.samples_seen = 0
        self.accepted_samples = 0
        self.rejected_samples = 0
        self._rng = random.Random(self.random_seed)
        self._reservoirs: dict[str, list[float]] = {
            column: [] for column in self.feature_columns
        }
        self._row_reservoir: list[list[float]] = []
        self._statistics_cache: dict[str, tuple[float, float, float, float, float]] = {}
        self._last_statistics_sample_count = -1
        self._detector: IsolationForest | None = None
        self._detector_threshold: float | None = None
        self._last_fit_accepted_samples = 0

    @property
    def ready(self) -> bool:
        return self.accepted_samples >= self.min_baseline_samples

    @property
    def detector_ready(self) -> bool:
        return self._detector is not None and self._detector_threshold is not None

    def _value(self, features: Mapping[str, float], column: str) -> float:
        value = float(features[column])
        if not math.isfinite(value):
            raise ValueError(f"Non-finite value for feature {column!r}")
        return value

    def observe(self, features: Mapping[str, float]) -> None:
        """Add one trusted normal feature row to the bounded profile."""
        values = [self._value(features, column) for column in self.feature_columns]
        self.samples_seen += 1
        self.accepted_samples += 1

        if len(self._row_reservoir) < self.reservoir_size:
            self._row_reservoir.append(values)
            replacement_index = len(self._row_reservoir) - 1
        else:
            replacement_index = self._rng.randrange(self.accepted_samples)
            if replacement_index < self.reservoir_size:
                self._row_reservoir[replacement_index] = values
            else:
                replacement_index = None

        for column, value in zip(self.feature_columns, values):
            reservoir = self._reservoirs[column]
            if len(reservoir) < self.reservoir_size:
                reservoir.append(value)
            elif replacement_index is not None:
                # Keep the feature and row reservoirs aligned.
                reservoir[replacement_index] = value

        self._statistics_cache.clear()
        if (
            self._detector is not None
            and self.accepted_samples - self._last_fit_accepted_samples >= self.refit_interval
        ):
            self._detector = None
            self._detector_threshold = None

    def reject(self) -> None:
        """Record a row that was deliberately excluded from learning."""
        self.samples_seen += 1
        self.rejected_samples += 1

    def _statistics(self, column: str) -> tuple[float, float, float, float, float]:
        cached = self._statistics_cache.get(column)
        if cached is not None:
            return cached
        values = np.asarray(self._reservoirs[column], dtype=float)
        if values.size == 0:
            statistics = (0.0, 0.0, 0.0, 0.0, 0.0)
        else:
            q01, q25, median, q75, q99 = np.percentile(
                values, [1, 25, 50, 75, 99]
            )
            statistics = (
                float(q01),
                float(q25),
                float(median),
                float(q75),
                float(q99),
            )
        self._statistics_cache[column] = statistics
        self._last_statistics_sample_count = self.accepted_samples
        return statistics

    def _fit_detector(self) -> None:
        if not self.ready or len(self._row_reservoir) < 32:
            return
        matrix = np.asarray(self._row_reservoir, dtype=float)
        detector = IsolationForest(
            n_estimators=128,
            max_samples=min(256, len(matrix)),
            contamination="auto",
            random_state=self.random_seed,
            n_jobs=1,
        )
        detector.fit(matrix)
        training_scores = detector.decision_function(matrix)
        # Reserve approximately the lowest 1% of trusted baseline scores as
        # local anomalies. This is a calibration choice, not a claim about
        # attack prevalence, and is exposed in the saved profile summary.
        self._detector = detector
        self._detector_threshold = float(np.percentile(training_scores, 1.0))
        self._last_fit_accepted_samples = self.accepted_samples

    def _ensure_detector(self) -> None:
        if self.ready and not self.detector_ready:
            self._fit_detector()

    def score(
        self,
        features: Mapping[str, float],
        outlier_z: float = 4.0,
        anomaly_z: float = 6.0,
        min_outlier_features: int = 3,
    ) -> dict:
        """Score a row against the local profile."""
        if outlier_z <= 0 or anomaly_z <= outlier_z:
            raise ValueError("Require 0 < outlier_z < anomaly_z")
        if min_outlier_features < 1:
            raise ValueError("min_outlier_features must be positive")

        values = {column: self._value(features, column) for column in self.feature_columns}
        if not self.ready:
            return {
                "ready": False,
                "detector_ready": False,
                "local_score": 0.0,
                "max_robust_z": 0.0,
                "outlier_feature_count": 0,
                "local_anomaly": False,
                "profile_samples": self.accepted_samples,
            }

        robust_z_values: dict[str, float] = {}
        for column, value in values.items():
            q01, q25, _median, q75, q99 = self._statistics(column)
            iqr = max(q75 - q25, 0.0)
            absolute_floor = 0.02 if ("ratio" in column or "entropy" in column) else 1.0
            lower_scale = max(q25 - q01, iqr / 2.0, absolute_floor)
            upper_scale = max(q99 - q75, iqr / 2.0, absolute_floor)
            if value < q01:
                robust_z_values[column] = (q01 - value) / lower_scale
            elif value > q99:
                robust_z_values[column] = (value - q99) / upper_scale
            else:
                robust_z_values[column] = 0.0

        ordered = sorted(robust_z_values.values(), reverse=True)
        max_robust_z = float(ordered[0]) if ordered else 0.0
        outlier_count = sum(value >= outlier_z for value in ordered)
        self._ensure_detector()

        if self.detector_ready:
            matrix = np.asarray([[values[column] for column in self.feature_columns]])
            detector_score = float(self._detector.decision_function(matrix)[0])
            local_score = float(
                max(0.0, (float(self._detector_threshold) - detector_score) * 10.0)
            )
            local_anomaly = bool(detector_score < float(self._detector_threshold))
        else:
            detector_score = 0.0
            local_score = float(np.mean(ordered[:3])) if ordered else 0.0
            local_anomaly = bool(
                max_robust_z >= anomaly_z or outlier_count >= min_outlier_features
            )

        return {
            "ready": True,
            "detector_ready": self.detector_ready,
            "local_score": local_score,
            "detector_score": detector_score,
            "detector_threshold": self._detector_threshold,
            "max_robust_z": max_robust_z,
            "outlier_feature_count": int(outlier_count),
            "local_anomaly": local_anomaly,
            "profile_samples": self.accepted_samples,
            "top_features": [
                column
                for column, _value in sorted(
                    robust_z_values.items(), key=lambda item: item[1], reverse=True
                )[:5]
            ],
        }

    def summary(self) -> dict:
        return {
            "format_version": self.FORMAT_VERSION,
            "organization_id": self.organization_id,
            "feature_count": len(self.feature_columns),
            "min_baseline_samples": self.min_baseline_samples,
            "reservoir_size": self.reservoir_size,
            "refit_interval": self.refit_interval,
            "samples_seen": self.samples_seen,
            "accepted_samples": self.accepted_samples,
            "rejected_samples": self.rejected_samples,
            "ready": self.ready,
            "detector_ready": self.detector_ready,
            "detector_threshold": self._detector_threshold,
            "last_fit_accepted_samples": self._last_fit_accepted_samples,
        }

    def to_dict(self) -> dict:
        return {
            **self.summary(),
            "feature_columns": self.feature_columns,
            "random_seed": self.random_seed,
            "reservoirs": self._reservoirs,
            "row_reservoir": self._row_reservoir,
        }

    def save(self, path: str | Path) -> None:
        """Atomically save the organization profile as JSON."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
        temporary.replace(target)

    @classmethod
    def load(cls, path: str | Path) -> "AdaptiveBaseline":
        target = Path(path)
        with target.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if payload.get("format_version") != cls.FORMAT_VERSION:
            raise ValueError("Unsupported adaptive profile format")
        profile = cls(
            feature_columns=list(payload["feature_columns"]),
            organization_id=str(payload["organization_id"]),
            min_baseline_samples=int(payload["min_baseline_samples"]),
            reservoir_size=int(payload["reservoir_size"]),
            refit_interval=int(payload.get("refit_interval", 2_048)),
            random_seed=int(payload.get("random_seed", 42)),
        )
        profile.samples_seen = int(payload.get("samples_seen", 0))
        profile.accepted_samples = int(payload.get("accepted_samples", 0))
        profile.rejected_samples = int(payload.get("rejected_samples", 0))
        reservoirs = payload.get("reservoirs", {})
        for column in profile.feature_columns:
            values = reservoirs.get(column, [])
            if len(values) > profile.reservoir_size:
                raise ValueError(f"Reservoir too large for feature {column!r}")
            profile._reservoirs[column] = [float(value) for value in values]

        row_reservoir = payload.get("row_reservoir")
        if row_reservoir is None:
            # Compatibility for profiles written by the first isolated
            # prototype: reconstruct aligned rows from per-feature reservoirs.
            row_count = min(
                [len(profile._reservoirs[column]) for column in profile.feature_columns]
                or [0]
            )
            row_reservoir = [
                [profile._reservoirs[column][index] for column in profile.feature_columns]
                for index in range(row_count)
            ]
        if len(row_reservoir) > profile.reservoir_size:
            raise ValueError("row_reservoir is larger than reservoir_size")
        profile._row_reservoir = [
            [float(value) for value in row] for row in row_reservoir
        ]
        profile._statistics_cache.clear()
        profile._detector = None
        profile._detector_threshold = None
        profile._last_fit_accepted_samples = 0
        return profile

    @classmethod
    def load_or_create(
        cls,
        path: str | Path,
        feature_columns: list[str],
        organization_id: str,
        min_baseline_samples: int = 172_800,
        reservoir_size: int = 2_048,
        refit_interval: int = 2_048,
        random_seed: int = 42,
    ) -> "AdaptiveBaseline":
        target = Path(path)
        if target.exists():
            profile = cls.load(target)
            if profile.organization_id != organization_id:
                raise ValueError(
                    "Profile organization_id does not match requested organization"
                )
            if profile.feature_columns != list(feature_columns):
                raise ValueError("Profile feature schema does not match detector schema")
            return profile
        return cls(
            feature_columns=feature_columns,
            organization_id=organization_id,
            min_baseline_samples=min_baseline_samples,
            reservoir_size=reservoir_size,
            refit_interval=refit_interval,
            random_seed=random_seed,
        )


__all__ = ["AdaptiveBaseline"]


if __name__ == "__main__":
    print("AdaptiveBaseline module loaded. Use adaptive_detect_v3.py for the runner.")
