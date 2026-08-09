"""
BlackBox Sentinel — M3 ML: Real-Time Anomaly Scoring
Loads trained Isolation Forest model and scores incoming packets.
Supports calibration mode (learn baseline) and armed mode (detect anomalies).

Author: M3 ML Engineer
Branch: m3-dev
"""

import os
import json
import time
import numpy as np
import joblib
from datetime import datetime, timezone
from enum import Enum


class DeviceState(Enum):
    CALIBRATING = "calibrating"
    ARMED = "armed"
    ALERT = "alert"
    LOCKDOWN = "lockdown"


# ─── Configuration ────────────────────────────────────────────
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_FILE = os.path.join(MODEL_DIR, "isolation_forest.joblib")
SCALER_FILE = os.path.join(MODEL_DIR, "scaler.joblib")
STATE_FILE = os.path.join(MODEL_DIR, "device_state.json")

# Calibration window (seconds) — 30 min for demo, 48h in production
CALIBRATION_WINDOW = 30 * 60  # 1800 seconds for demo
ANOMALY_THRESHOLD = 0.0       # Standard Isolation Forest decision boundary (<0 is anomalous)


class AnomalyScorer:
    """
    Real-time anomaly scoring engine with calibration support.
    
    Lifecycle:
        1. CALIBRATING: Collecting baseline traffic features
        2. ARMED: Model trained, scoring live traffic
        3. ALERT: Anomaly detected, waiting for response
        4. LOCKDOWN: Relay fired, line cut, awaiting PIN override
    """

    def __init__(self):
        self.state = DeviceState.CALIBRATING
        self.model = None
        self.scaler = None
        self.calibration_buffer = []
        self.calibration_start = None
        self._load_state()

    def _load_state(self):
        """Restore state and model if previously saved."""
        if os.path.exists(MODEL_FILE) and os.path.exists(SCALER_FILE):
            try:
                self.model = joblib.load(MODEL_FILE)
                self.scaler = joblib.load(SCALER_FILE)
                self.state = DeviceState.ARMED
                print("[SCORER] Loaded existing model — state: ARMED")
            except Exception as e:
                print(f"[SCORER] Failed to load model: {e}")
                self.state = DeviceState.CALIBRATING

    def start_calibration(self):
        """Begin calibration mode — collect baseline traffic."""
        self.state = DeviceState.CALIBRATING
        self.calibration_buffer = []
        self.calibration_start = time.time()
        print(f"[CALIBRATE] Started — collecting baseline for {CALIBRATION_WINDOW}s")
        self._save_state()

    def ingest_features(self, features: dict) -> dict:
        """
        Process a single packet's features.
        
        Args:
            features: dict with keys (packet_size, inter_arrival, protocol, src_port, dst_port)
        
        Returns:
            dict with score, is_anomaly, and current state
        """
        feature_vector = np.array([[
            features["packet_size"],
            features["inter_arrival"],
            features["protocol"],
            features["src_port"],
            features["dst_port"]
        ]])

        # ── Calibrating: buffer features ──
        if self.state == DeviceState.CALIBRATING:
            self.calibration_buffer.append(feature_vector[0])

            elapsed = time.time() - (self.calibration_start or time.time())
            if elapsed >= CALIBRATION_WINDOW and len(self.calibration_buffer) >= 100:
                self._train_from_calibration()

            return {
                "state": self.state.value,
                "score": 0.0,
                "is_anomaly": False,
                "samples_collected": len(self.calibration_buffer),
                "calibration_remaining": max(0, CALIBRATION_WINDOW - elapsed)
            }

        # ── Armed: score against model ──
        if self.state in (DeviceState.ARMED, DeviceState.ALERT):
            scaled = self.scaler.transform(feature_vector)
            score = float(self.model.decision_function(scaled)[0])
            is_anomaly = score < ANOMALY_THRESHOLD

            if is_anomaly:
                self.state = DeviceState.ALERT

            return {
                "state": self.state.value,
                "score": score,
                "is_anomaly": is_anomaly,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # ── Lockdown: relay fired, no scoring ──
        return {
            "state": self.state.value,
            "score": 0.0,
            "is_anomaly": False,
            "message": "System in lockdown — awaiting PIN override"
        }

    def _train_from_calibration(self):
        """Train Isolation Forest on collected calibration data."""
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler

        print(f"[CALIBRATE] Training on {len(self.calibration_buffer)} baseline samples...")
        
        X = np.array(self.calibration_buffer)
        
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = IsolationForest(
            n_estimators=200,
            contamination=0.05,
            random_state=42,
            n_jobs=-1
        )
        self.model.fit(X_scaled)

        # Persist
        os.makedirs(MODEL_DIR, exist_ok=True)
        joblib.dump(self.model, MODEL_FILE)
        joblib.dump(self.scaler, SCALER_FILE)

        self.state = DeviceState.ARMED
        self.calibration_buffer = []
        self._save_state()
        print("[CALIBRATE] Complete — state: ARMED")

    def trigger_lockdown(self):
        """Called when relay fires — enter lockdown state."""
        self.state = DeviceState.LOCKDOWN
        self._save_state()

    def pin_override(self, pin: str, correct_pin: str = "1234") -> bool:
        """
        PIN override to exit lockdown and re-engage relay.
        
        Returns True if PIN is correct and lockdown is lifted.
        """
        if pin == correct_pin:
            self.state = DeviceState.ARMED
            self._save_state()
            print("[OVERRIDE] PIN accepted — state: ARMED")
            return True
        print("[OVERRIDE] PIN rejected")
        return False

    def _save_state(self):
        """Persist device state to disk."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        state_data = {
            "state": self.state.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state_data, f)


# ─── Standalone test ──────────────────────────────────────────
if __name__ == "__main__":
    scorer = AnomalyScorer()
    
    # Simulate calibration with fake data
    scorer.start_calibration()
    scorer.calibration_start = time.time() - CALIBRATION_WINDOW  # skip wait
    
    for i in range(150):
        result = scorer.ingest_features({
            "packet_size": np.random.normal(500, 100),
            "inter_arrival": np.random.exponential(0.01),
            "protocol": 6,  # TCP
            "src_port": np.random.randint(1024, 65535),
            "dst_port": 80
        })
    
    print(f"\n[TEST] State after calibration: {scorer.state.value}")
    
    # Score a normal packet
    result = scorer.ingest_features({
        "packet_size": 450,
        "inter_arrival": 0.01,
        "protocol": 6,
        "src_port": 45000,
        "dst_port": 80
    })
    print(f"[TEST] Normal packet — score: {result['score']:.4f}, anomaly: {result['is_anomaly']}")
    
    # Score a suspicious packet
    result = scorer.ingest_features({
        "packet_size": 10000,
        "inter_arrival": 5.0,
        "protocol": 17,  # UDP
        "src_port": 4444,
        "dst_port": 4444
    })
    print(f"[TEST] Suspicious packet — score: {result['score']:.4f}, anomaly: {result['is_anomaly']}")
