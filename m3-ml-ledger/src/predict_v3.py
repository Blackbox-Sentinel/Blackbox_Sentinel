"""M3 v3 predictor adapter for the master Sentinel pipeline.

This adapter preserves the state/result interface expected by
``sentinel_pipeline.py`` while replacing the legacy five-feature Isolation
Forest with the validated 45-feature v3 model plus an organization-specific
adaptive profile.

The legacy ``predict.py`` remains untouched as a rollback path.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
ML_ROOT = REPO_ROOT / "ml"
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from adaptive_baseline import AdaptiveBaseline
from feature_pipeline_v2 import RollingFeatureState, model_feature_columns


class DeviceState(Enum):
    CALIBRATING = "calibrating"
    ARMED = "armed"
    ALERT = "alert"
    LOCKDOWN = "lockdown"


MODEL_PATH = Path(
    os.getenv(
        "SENTINEL_V3_MODEL",
        str(ML_ROOT / "models" / "sentinel_model_v3_stratified_candidate.pkl"),
    )
)
METRICS_PATH = Path(
    os.getenv(
        "SENTINEL_V3_METRICS",
        str(ML_ROOT / "models" / "sentinel_model_v3_stratified_metrics.json"),
    )
)
DEFAULT_ORGANIZATION = "default_organization"
DEFAULT_PROFILE_ROOT = ML_ROOT / "adaptive_profiles"
HISTORY_WINDOWS = 5
BASELINE_DURATION = float(os.getenv("SENTINEL_BASELINE_SECONDS", "172800"))
MIN_BASELINE_SAMPLES = int(os.getenv("SENTINEL_MIN_BASELINE_SAMPLES", "2048"))
BASELINE_ACCEPT_PROBABILITY = float(
    os.getenv("SENTINEL_BASELINE_ACCEPT_PROBABILITY", "0.25")
)
FORCE_RECALIBRATION = os.getenv("SENTINEL_FORCE_RECALIBRATION", "0") == "1"
PROFILE_SAVE_INTERVAL = int(os.getenv("SENTINEL_PROFILE_SAVE_INTERVAL", "60"))


def safe_organization_name(value: str) -> str:
    """Return a filesystem-safe, stable identifier for one organization."""
    cleaned = "".join(
        character if character.isalnum() or character in ("-", "_") else "_"
        for character in value.strip()
    )
    if not cleaned:
        raise ValueError("organization_id must contain at least one valid character")
    return cleaned[:120]


class AnomalyScorer:
    """45-feature v3 scorer with the legacy pipeline-compatible interface."""

    def __init__(
        self,
        organization_id: str | None = None,
        profile_path: str | Path | None = None,
        state_file: str | Path | None = None,
    ):
        explicit_organization = organization_id is not None
        requested_organization = organization_id or os.getenv(
            "SENTINEL_ORGANIZATION_ID", DEFAULT_ORGANIZATION
        )
        self.organization_id = safe_organization_name(requested_organization)
        profile_root = Path(
            os.getenv("SENTINEL_PROFILE_ROOT", str(DEFAULT_PROFILE_ROOT))
        )
        state_root = Path(os.getenv("SENTINEL_STATE_ROOT", str(profile_root)))
        if profile_path is not None:
            self.profile_path = Path(profile_path)
        elif not explicit_organization and os.getenv("SENTINEL_PROFILE_PATH"):
            self.profile_path = Path(os.environ["SENTINEL_PROFILE_PATH"])
        else:
            self.profile_path = profile_root / f"{self.organization_id}_profile.json"
        if state_file is not None:
            self.state_file = Path(state_file)
        elif not explicit_organization and os.getenv("SENTINEL_V3_STATE_FILE"):
            self.state_file = Path(os.environ["SENTINEL_V3_STATE_FILE"])
        else:
            self.state_file = state_root / f"{self.organization_id}_state.json"

        self.feature_columns = model_feature_columns(HISTORY_WINDOWS)
        self.history_state = RollingFeatureState(HISTORY_WINDOWS)
        self.state = DeviceState.CALIBRATING
        self.model = None
        self.threshold = 0.55
        self.profile: AdaptiveBaseline | None = None
        self.calibration_start: float | None = None
        self.last_result: dict = {}
        self.window_count = 0
        self._load_model()
        self._load_profile()
        self._load_state()

    def _load_model(self) -> None:
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(f"v3 model not found: {MODEL_PATH}")
        if not METRICS_PATH.is_file():
            raise FileNotFoundError(f"v3 metrics not found: {METRICS_PATH}")

        import pickle

        with MODEL_PATH.open("rb") as handle:
            self.model = pickle.load(handle)
        with METRICS_PATH.open("r", encoding="utf-8") as handle:
            metrics = json.load(handle)
        self.threshold = float(metrics["selected_threshold"])
        print(
            f"[SCORER] Loaded v3 model ({len(self.feature_columns)} features) — "
            f"threshold: {self.threshold:.2f}"
        )

    def _load_profile(self) -> None:
        self.profile = AdaptiveBaseline.load_or_create(
            self.profile_path,
            feature_columns=self.feature_columns,
            organization_id=self.organization_id,
            min_baseline_samples=MIN_BASELINE_SAMPLES,
            reservoir_size=2_048,
            refit_interval=2_048,
        )
        print(
            f"[SCORER] Organization profile: {self.organization_id} — "
            f"{self.profile.accepted_samples} accepted windows, "
            f"ready={self.profile.ready}"
        )

    def _load_state(self) -> None:
        if self.state_file.exists() and not FORCE_RECALIBRATION:
            try:
                with self.state_file.open("r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                if payload.get("state") == DeviceState.LOCKDOWN.value:
                    self.state = DeviceState.LOCKDOWN
                elif self.profile is not None and self.profile.ready:
                    self.state = DeviceState.ARMED
            except (OSError, ValueError, TypeError):
                self.state = DeviceState.CALIBRATING

    def start_calibration(self):
        """Begin or resume the organization baseline phase."""
        if self.profile is not None and self.profile.ready and not FORCE_RECALIBRATION:
            self.state = DeviceState.ARMED
            self.calibration_start = None
            print(
                "[CALIBRATE] Existing organization profile is ready — "
                "starting in ARMED mode"
            )
            self._save_state()
            return

        self.state = DeviceState.CALIBRATING
        self.calibration_start = time.time()
        print(
            f"[CALIBRATE] Learning organization {self.organization_id} for "
            f"{BASELINE_DURATION:.0f}s; local alerts remain disabled during warm-up"
        )
        self._save_state()

    def ingest_feature_window(self, feature_row: Mapping[str, float]) -> dict:
        """Process one complete 45-feature v3 window."""
        if self.profile is None or self.model is None:
            raise RuntimeError("Scorer is not initialized")

        self.window_count += 1
        vector = pd.DataFrame(
            [[float(feature_row[column]) for column in self.feature_columns]],
            columns=self.feature_columns,
        )
        probability = float(self.model.predict_proba(vector)[0, 1])
        local = self.profile.score(feature_row)

        elapsed = (
            time.time() - self.calibration_start
            if self.calibration_start is not None
            else BASELINE_DURATION
        )
        local_enabled = bool(
            self.profile.ready and elapsed >= BASELINE_DURATION and self.state != DeviceState.LOCKDOWN
        )
        global_attack = probability >= self.threshold
        local_attack = bool(local.get("local_anomaly", False))
        eligible_for_learning = bool(
            probability <= BASELINE_ACCEPT_PROBABILITY and not local_attack
        )

        if eligible_for_learning:
            self.profile.observe(feature_row)
        else:
            self.profile.reject()
        if self.window_count % max(1, PROFILE_SAVE_INTERVAL) == 0:
            self.profile.save(self.profile_path)

        combined_attack = bool(global_attack or (local_enabled and local_attack))
        if self.state != DeviceState.LOCKDOWN:
            if combined_attack:
                self.state = DeviceState.ALERT
            elif local_enabled:
                self.state = DeviceState.ARMED
            else:
                self.state = DeviceState.CALIBRATING

        score = max(
            probability,
            float(local.get("local_score", 0.0)) / 10.0,
        )
        result = {
            "state": self.state.value,
            "score": score,
            "probability_attack": probability,
            "threshold": self.threshold,
            "is_anomaly": combined_attack,
            "global_prediction": "ATTACK" if global_attack else "BENIGN",
            "local_prediction": (
                "ANOMALY" if local_attack else "NORMAL"
            )
            if local_enabled
            else "LEARNING",
            "local_detection_enabled": local_enabled,
            "organization_id": self.organization_id,
            "profile_ready": self.profile.ready,
            "profile_samples": self.profile.accepted_samples,
            "eligible_for_learning": eligible_for_learning,
            "local_score": float(local.get("local_score", 0.0)),
            "top_local_features": list(local.get("top_features", [])),
            "feature_count": len(self.feature_columns),
            "timestamp": str(
                feature_row.get(
                    "timestamp", datetime.now(timezone.utc).isoformat()
                )
            ),
        }
        self.last_result = result
        if self.window_count % max(1, PROFILE_SAVE_INTERVAL) == 0:
            self._save_state()
        return result

    def save_profile(self) -> None:
        """Persist the profile and state during graceful shutdown."""
        if self.profile is not None:
            self.profile.save(self.profile_path)
        self._save_state()

    def ingest_features(self, features: dict) -> dict:
        """Reject the legacy five-feature interface explicitly.

        Keeping this method makes accidental legacy calls fail loudly rather
        than silently feeding an invalid vector to the v3 model.
        """
        raise ValueError(
            "The v3 scorer requires a complete 45-feature window. "
            "Use ingest_feature_window() after feature_pipeline_v2.py conversion."
        )

    def trigger_lockdown(self):
        """Called by the master pipeline after an alert response."""
        self.state = DeviceState.LOCKDOWN
        self._save_state()

    def pin_override(self, pin: str, correct_pin: str = "1234") -> bool:
        if pin == correct_pin:
            self.state = DeviceState.ARMED
            self._save_state()
            print("[OVERRIDE] PIN accepted — state: ARMED")
            return True
        print("[OVERRIDE] PIN rejected")
        return False

    def _save_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        state_data = {
            "state": self.state.value,
            "organization_id": self.organization_id,
            "profile": str(self.profile_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self.state_file.open("w", encoding="utf-8") as handle:
            json.dump(state_data, handle, indent=2)


__all__ = ["AnomalyScorer", "DeviceState"]
