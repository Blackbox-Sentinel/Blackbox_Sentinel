import numpy as np
from pathlib import Path
import sys
import os

# Ensure ml is in path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "m3-ml-ledger" / "src"))
sys.path.insert(0, str(ROOT / "ml"))

from predict_v3 import AnomalyScorer
from feature_pipeline_v2 import model_feature_columns

def test_adaptive_baseline_rejects_edge_case_anomalies(tmp_path):
    """
    Verify that when the AnomalyScorer is in calibration mode, it correctly
    rejects edge-case anomalies (like a packet storm) from the baseline profile
    to prevent over-calibration to attack traffic.
    """
    os.environ["SENTINEL_MIN_BASELINE_SAMPLES"] = "10"
    
    # Initialize the v3 Scorer
    scorer = AnomalyScorer(organization_id="test_org")
    scorer.start_calibration()
    
    # 1. Feed a completely benign packet window
    benign_features = {col: 0.0 for col in model_feature_columns()}
    benign_features["packets_per_sec"] = 10.0
    benign_features["bytes_per_sec"] = 5000.0
    
    # The baseline should ACCEPT the benign traffic
    scorer.ingest_feature_window(benign_features)
    assert scorer.profile.accepted_samples == 1
    assert scorer.profile.rejected_samples == 0

    # 2. Feed an edge-case anomaly (massive packet storm triggering high probability)
    # The scorer will see the probability_attack spike and must NOT observe it.
    anomalous_features = {col: 1000000.0 for col in model_feature_columns()}
    
    scorer.ingest_feature_window(anomalous_features)
    
    # The baseline should REJECT the anomalous traffic
    assert scorer.profile.accepted_samples == 1
    assert scorer.profile.rejected_samples == 1
    
    print("\nVerification Passed: Edge-case anomaly correctly rejected during calibration!")

if __name__ == "__main__":
    test_adaptive_baseline_rejects_edge_case_anomalies(Path("test_profile_dir"))
