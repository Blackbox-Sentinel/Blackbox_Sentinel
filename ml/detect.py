import pandas as pd
import os
import joblib
from ml.feature_extract import extract_features
from ledger.ledger import append_entry
from security.zeroization import execute_zeroization

print("Loading model...")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")

model = joblib.load(MODEL_PATH)
print("Capturing live traffic...")

row = extract_features()

columns = [
    "packets_per_sec",
    "avg_packet_size",
    "max_packet_size",
    "min_packet_size",
    "tcp_count",
    "udp_count",
    "icmp_count",
    "unique_src_ips",
    "unique_dst_ips",
    "syn_count",
    "ack_count",
    "fin_count",
    "rst_count",
    "psh_count",
    "urg_count",
    "syn_ratio",
    "ack_ratio",
    "fin_ratio",
    "rst_ratio",
    "psh_ratio",
    "urg_ratio"
]

features = pd.DataFrame([row[1:]], columns=columns)

prediction = model.predict(features)[0]
score = model.decision_function(features)[0]

print("\n========== RESULT ==========")

if prediction == 1:

    print("Traffic Status : NORMAL")

    append_entry("NORMAL")

else:

    print("Traffic Status : ANOMALY")

    secrets = {
        "api_key": bytearray(b"MY_SECRET_API_KEY"),
        "password": bytearray(b"SuperPassword123"),
        "session_token": bytearray(b"abcdef123456")
    }

    execute_zeroization(secrets)

    append_entry("ANOMALY DETECTED")

    append_entry("ZEROIZATION EXECUTED")

print(f"Anomaly Score  : {score:.4f}")