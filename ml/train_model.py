import logging
import os

import joblib
import numpy as np
from preprocess import engineer_features, load_dataset
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    # ============================================
    # Load Dataset
    # ============================================

    logger.info("=" * 60)
    logger.info("Loading Dataset...")
    logger.info("=" * 60)

    dataset_path = os.path.join(BASE_DIR, "data", "DSL-StrongPasswordData.csv")
    dataset = load_dataset(dataset_path)

    logger.info("\nEngineering Features...")

    processed = engineer_features(dataset)


    # ============================================
    # Data Cleaning
    # ============================================

    logger.info("\nCleaning Dataset...")

    # Remove invalid values
    processed = processed.replace([np.inf, -np.inf], np.nan)
    processed = processed.dropna()

    # Remove negative values
    processed = processed.clip(lower=0)

    logger.info(f"Samples after cleaning: {len(processed)}")


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

    logger.info(f"\nTraining Shape: {X_train.shape}")


    # ============================================
    # Train Isolation Forest
    # ============================================

    logger.info("\nTraining Isolation Forest...")

    model = IsolationForest(
        n_estimators=300,
        contamination=0.10,
        random_state=42
    )

    model.fit(X_train)

    logger.info("Training Completed Successfully!")


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

    logger.info("\nModel Saved Successfully!")
    logger.info(MODEL_PATH)

    logger.info("=" * 60)
    logger.info("TrustGuard AI Model Ready")
    logger.info("=" * 60)