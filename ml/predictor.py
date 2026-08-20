import logging
import os

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# Base path for models
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "scaler.pkl")

# Load model and scaler lazily or at module load time
model = None
scaler = None

def reload_model():
    """
    Hot-reloads model and scaler from disk.
    """
    global model, scaler
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        logger.info("✅ TrustGuard AI model hot-reloaded successfully.")

try:
    reload_model()
except (OSError, FileNotFoundError, ValueError) as e:
    logger.error(f"❌ Failed to load ML model: {e}")


DECISION_SCORE_MIN = -0.3
DECISION_SCORE_MAX = 0.3
DECISION_SCORE_SCALE = DECISION_SCORE_MAX - DECISION_SCORE_MIN


def predict_trust_score(features: dict) -> int:
    """
    Predicts a trust score (0-100) based on extracted telemetry features.
    If the model is not loaded, uses a fallback heuristic based on feature thresholds.
    """
    if model is None or scaler is None:
        # Fallback heuristic calculation if model loading failed
        return _fallback_trust_score(features)

    try:
        # Extract features in exact order used during training:
        # ["avg_dwell_time_ms", "std_dwell_time_ms", "avg_flight_time_ms", "std_flight_time_ms", "typing_speed_cps"]
        input_data = np.array([[
            features.get("avg_dwell_time_ms", 0.0),
            features.get("std_dwell_time_ms", 0.0),
            features.get("avg_flight_time_ms", 0.0),
            features.get("std_flight_time_ms", 0.0),
            features.get("typing_speed_cps", 0.0)
        ]])

        # Scale features
        scaled_data = scaler.transform(input_data)

        # Get raw decision score from Isolation Forest (higher = more normal, lower = anomalous)
        raw_score = model.decision_function(scaled_data)[0]

        # Convert decision score to 0-100 trust score
        trust_score = _decision_score_to_trust_score(raw_score)
        return trust_score

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"Error predicting trust score: {e}")
        return _fallback_trust_score(features)


def _decision_score_to_trust_score(decision_score: float) -> int:
    """
    Converts raw Isolation Forest decision_function score (-0.3 to +0.3)
    into a human-readable Trust Score (0 to 100).
    """
    decision_score = max(DECISION_SCORE_MIN, min(DECISION_SCORE_MAX, decision_score))
    raw_trust = ((decision_score - DECISION_SCORE_MIN) / DECISION_SCORE_SCALE) * 100.0
    trust_score_int = round(raw_trust)
    return max(0, min(100, trust_score_int))


def _fallback_trust_score(features: dict) -> int:
    """
    Rule-based fallback calculation if ML model fails to load.
    """
    dwell = features.get("avg_dwell_time_ms", 100.0)
    std_dwell = features.get("std_dwell_time_ms", 10.0)
    flight = features.get("avg_flight_time_ms", 150.0)
    std_flight = features.get("std_flight_time_ms", 15.0)

    score = 100.0

    # Penalize bot-like zero-variance behavior
    if std_dwell <= 0.0 and std_flight <= 0.0:
        score -= 80.0

    # Penalize extreme dwell times
    if dwell < 40.0 or dwell > 400.0:
        score -= 30.0

    # Penalize extreme flight times
    if flight < 10.0 or flight > 800.0:
        score -= 30.0

    return max(0, min(100, round(score)))