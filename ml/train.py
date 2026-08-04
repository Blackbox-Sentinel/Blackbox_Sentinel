from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

BASE_DIR = Path(__file__).resolve().parent

CSV_FILE = BASE_DIR / "traffic.csv"
MODEL_FILE = BASE_DIR / "model.pkl"

print(f"Loading dataset from: {CSV_FILE}")

data = pd.read_csv(CSV_FILE)

print(f"Dataset loaded: {len(data)} samples")

# Remove timestamp column
X = data.drop(columns=["timestamp"])

model = IsolationForest(
    n_estimators=100,
    contamination=0.02,
    random_state=42
)

print("Training model...")

model.fit(X)

joblib.dump(model, MODEL_FILE)

print("Training complete.")
print(f"Model saved to: {MODEL_FILE}")