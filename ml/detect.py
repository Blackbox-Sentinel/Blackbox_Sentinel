import joblib
from feature_extract import extract_features

print("Loading model...")

model = joblib.load("model.pkl")

print("Capturing live traffic...")

row = extract_features()

# Remove timestamp
features = row[1:]

prediction = model.predict([features])[0]
score = model.decision_function([features])[0]

print("\n========== RESULT ==========")

if prediction == 1:
    print("Traffic Status : NORMAL")
else:
    print("Traffic Status : ANOMALY")

print(f"Anomaly Score  : {score:.4f}")