import json
import logging
import os

import joblib
import numpy as np
from preprocess import engineer_features, load_dataset
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FEATURE_NAMES = [
    "avg_dwell_time_ms",
    "std_dwell_time_ms",
    "avg_flight_time_ms",
    "std_flight_time_ms",
    "typing_speed_cps",
    "dwell_flight_ratio",
    "pause_frequency",
]


def train_production_model(dataset_path: str | None = None):
    """Train the same 7D Isolation Forest pipeline used by production inference."""
    dataset_path = dataset_path or os.path.join(BASE_DIR, "data", "DSL-StrongPasswordData.csv")

    logger.info("Loading dataset: %s", dataset_path)
    dataset = load_dataset(dataset_path)
    processed = engineer_features(dataset)

    processed = processed.replace([np.inf, -np.inf], np.nan).dropna().clip(lower=0)
    missing = [name for name in FEATURE_NAMES if name not in processed.columns]
    if missing:
        raise ValueError(f"Training features missing from preprocessing output: {missing}")

    X_train = processed[FEATURE_NAMES].values
    logger.info("Training shape: %s", X_train.shape)

    scaler = StandardScaler()
    scaled_X = scaler.fit_transform(X_train)

    model = IsolationForest(
        n_estimators=300,
        contamination=0.05,
        random_state=42,
    )
    model.fit(scaled_X)

    raw_scores = model.decision_function(scaled_X)
    p_min = float(np.percentile(raw_scores, 5))
    p_max = float(np.percentile(raw_scores, 95))

    model_path = os.path.join(BASE_DIR, "model.pkl")
    scaler_path = os.path.join(BASE_DIR, "scaler.pkl")
    calibration_path = os.path.join(BASE_DIR, "calibration.json")
    metadata_path = os.path.join(BASE_DIR, "model_metadata.json")

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    with open(calibration_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "p_min": round(p_min, 8),
                "p_max": round(p_max, 8),
                "selected_architecture": "Isolation Forest (Global Anomaly Detection)",
                "selected_feature_variant": "7D Extended Telemetry",
            },
            f,
            indent=2,
        )

    metadata = {
        "model_version": "local-retrain",
        "inference_model": "Isolation Forest",
        "profile_model": "Mahalanobis Distance",
        "feature_variant": "7D Extended Telemetry",
        "feature_indices": list(range(7)),
        "feature_names": FEATURE_NAMES,
        "training_samples": int(len(X_train)),
        "training_users": int(dataset["subject"].nunique()) if "subject" in dataset.columns else None,
        "contamination": 0.05,
        "random_seed": 42,
        "production_eer": None,
        "production_auc": None,
        "metrics_status": "PENDING_FRESH_EVALUATION",
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Model saved: %s", model_path)
    logger.info("Scaler saved: %s", scaler_path)
    logger.info("Production artifacts are internally consistent; biometric metrics require evaluate_model.py.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    train_production_model()
