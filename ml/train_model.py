import os
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from preprocess import load_dataset, engineer_features

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================
# Load Dataset
# ============================================

print("=" * 60)
print("Loading Dataset...")
print("=" * 60)

dataset_path = os.path.join(BASE_DIR, "data", "DSL-StrongPasswordData.csv")
dataset = load_dataset(dataset_path)

print("\nEngineering Features...")

processed = engineer_features(dataset)


# ============================================
# Data Cleaning
# ============================================

print("\nCleaning Dataset...")

# Remove invalid values
processed = processed.replace([np.inf, -np.inf], np.nan)
processed = processed.dropna()

# Remove negative values
processed = processed.clip(lower=0)

print("Samples after cleaning:", len(processed))


# ============================================
# Training Data
# ============================================

X_train = processed[
    [
        "avg_dwell_time_ms",
        "avg_flight_time_ms",
        "typing_speed_cps"
    ]
].values

print("\nTraining Shape:", X_train.shape)


# ============================================
# Train Isolation Forest
# ============================================

print("\nTraining Isolation Forest...")

model = IsolationForest(
    n_estimators=300,
    contamination=0.10,
    random_state=42
)

model.fit(X_train)

print("Training Completed Successfully!")


# ============================================
# Save Model
# ============================================

os.makedirs(os.path.join(BASE_DIR, "saved_model"), exist_ok=True)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "saved_model",
    "trust_model.pkl"
)

joblib.dump(model, MODEL_PATH)

print("\nModel Saved Successfully!")
print(MODEL_PATH)

print("=" * 60)
print("TrustGuard AI Model Ready")
print("=" * 60)