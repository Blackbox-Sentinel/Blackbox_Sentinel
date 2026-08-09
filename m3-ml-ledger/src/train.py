"""
BlackBox Sentinel — M3 ML: Isolation Forest Training
Extracts features from pcap files and trains an anomaly detection model.

Author: M3 ML Engineer
Branch: m3-dev
"""

import os
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

# ─── Configuration ────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_FILE = os.path.join(MODEL_DIR, "isolation_forest.joblib")
SCALER_FILE = os.path.join(MODEL_DIR, "scaler.joblib")

# Isolation Forest hyperparameters
CONTAMINATION = 0.05    # Expected fraction of anomalies
N_ESTIMATORS = 200
RANDOM_STATE = 42


def extract_features_from_pcap(pcap_path: str) -> pd.DataFrame:
    """
    Extract statistical features from a pcap file.
    Features: packet_size, inter_arrival_time, protocol_id, src_port, dst_port
    """
    from scapy.all import rdpcap, IP, TCP, UDP
    
    packets = rdpcap(pcap_path)
    records = []
    
    prev_time = None
    for pkt in packets:
        if IP in pkt:
            pkt_size = len(pkt)
            pkt_time = float(pkt.time)
            inter_arrival = (pkt_time - prev_time) if prev_time else 0.0
            prev_time = pkt_time
            
            protocol = pkt[IP].proto
            src_port = pkt[TCP].sport if TCP in pkt else (pkt[UDP].sport if UDP in pkt else 0)
            dst_port = pkt[TCP].dport if TCP in pkt else (pkt[UDP].dport if UDP in pkt else 0)
            
            records.append({
                "packet_size": pkt_size,
                "inter_arrival": inter_arrival,
                "protocol": protocol,
                "src_port": src_port,
                "dst_port": dst_port
            })
    
    return pd.DataFrame(records)


def train_model():
    """Train Isolation Forest on all pcap files in data directory."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    print("=== BlackBox Sentinel M3 — Model Training ===\n")
    
    # Collect features from all pcap files
    all_features = []
    pcap_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".pcap")]
    
    if not pcap_files:
        print(f"[ERROR] No .pcap files found in {DATA_DIR}")
        print("Run M2 capture first, or add sample pcap files to the data/ folder.")
        return
    
    for pcap_file in pcap_files:
        pcap_path = os.path.join(DATA_DIR, pcap_file)
        print(f"[EXTRACT] Processing {pcap_file}...")
        df = extract_features_from_pcap(pcap_path)
        all_features.append(df)
        print(f"  → Extracted {len(df)} packet features")
    
    # Combine and scale
    features_df = pd.concat(all_features, ignore_index=True)
    print(f"\n[DATA] Total samples: {len(features_df)}")
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features_df)
    
    # Train Isolation Forest
    print(f"[TRAIN] Training Isolation Forest (n_estimators={N_ESTIMATORS})...")
    model = IsolationForest(
        n_estimators=N_ESTIMATORS,
        contamination=CONTAMINATION,
        random_state=RANDOM_STATE,
        n_jobs=-1
    )
    model.fit(X_scaled)
    
    # Save model & scaler
    joblib.dump(model, MODEL_FILE)
    joblib.dump(scaler, SCALER_FILE)
    
    print(f"\n[SAVED] Model → {MODEL_FILE}")
    print(f"[SAVED] Scaler → {SCALER_FILE}")
    print("[DONE] Training complete!")


if __name__ == "__main__":
    train_model()
