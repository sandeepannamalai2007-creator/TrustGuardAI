import json
import logging
import os

import joblib
import numpy as np

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "scaler.pkl")
CALIBRATION_PATH = os.path.join(BASE_DIR, "calibration.json")
METADATA_PATH = os.path.join(BASE_DIR, "model_metadata.json")
ACTIVE_MODEL_PATH = os.path.join(BASE_DIR, "artifacts", "production", "active_model.json")

model = None
scaler = None
calibration_p_min = -0.20
calibration_p_max = 0.10
feature_indices = [0, 1, 2, 4]


def reload_model():
    """Load the production Isolation Forest, scaler, calibration and metadata."""
    global model, scaler, calibration_p_min, calibration_p_max, feature_indices

    if os.path.exists(ACTIVE_MODEL_PATH):
        try:
            with open(ACTIVE_MODEL_PATH, "r", encoding="utf-8") as f:
                act = json.load(f)
                logger.info(
                    "Active Model Registry: version='%s', activated_at='%s', previous='%s'",
                    act.get("active_version"),
                    act.get("activated_at"),
                    act.get("previous_version"),
                )
        except (OSError, ValueError) as e:
            logger.warning("Could not load active_model.json (%s).", e)

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Production model not found: {MODEL_PATH}")
    if not os.path.exists(SCALER_PATH):
        raise FileNotFoundError(f"Production scaler not found: {SCALER_PATH}")

    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    logger.info("Production Isolation Forest and StandardScaler loaded successfully.")

    if os.path.exists(CALIBRATION_PATH):
        try:
            with open(CALIBRATION_PATH, "r", encoding="utf-8") as f:
                cal_data = json.load(f)
            calibration_p_min = float(cal_data.get("p_min", -0.20))
            calibration_p_max = float(cal_data.get("p_max", 0.10))
            logger.info(
                "Empirical calibration loaded: p_min=%.4f, p_max=%.4f",
                calibration_p_min,
                calibration_p_max,
            )
        except (OSError, ValueError, TypeError) as e:
            logger.warning("Failed to load calibration parameters (%s). Using defaults.", e)

    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)
            feature_indices = [int(i) for i in meta.get("feature_indices", feature_indices)]
            logger.info(
                "Model metadata loaded: inference='%s', profile='%s', variant='%s', EER=%s, AUC=%s",
                meta.get("inference_model", "Isolation Forest"),
                meta.get("profile_model", "Mahalanobis"),
                meta.get("feature_variant", "Unknown"),
                meta.get("production_eer"),
                meta.get("production_auc"),
            )
        except (OSError, ValueError, TypeError) as e:
            logger.warning("Failed to load model metadata (%s). Using defaults.", e)


try:
    reload_model()
except (OSError, FileNotFoundError, ValueError, TypeError) as e:
    logger.error("Failed to load ML model artifacts: %s", e)


class MLModelUnavailableException(Exception):
    """Raised when the ML inference model or scaler is unavailable."""


def predict_trust_score(features: dict) -> int:
    """Predict an Isolation Forest trust score from 0 to 100."""
    if model is None or scaler is None:
        logger.warning("[SECURITY DEGRADED] ML model or scaler unavailable; failing closed.")
        raise MLModelUnavailableException("ML inference model unavailable.")

    try:
        avg_d = float(features.get("avg_dwell_time_ms", 0.0))
        std_d = float(features.get("std_dwell_time_ms", 0.0))
        avg_f = float(features.get("avg_flight_time_ms", 0.0))
        std_f = float(features.get("std_flight_time_ms", 0.0))
        speed = float(features.get("typing_speed_cps", 0.0))
        df_ratio = avg_d / (avg_f + 1e-5)
        pause_count = float(features.get("pause_count", 0.0))

        all_features = [avg_d, std_d, avg_f, std_f, speed, df_ratio, pause_count]
        input_vector = [all_features[idx] for idx in feature_indices]
        input_data = np.asarray([input_vector], dtype=float)

        scaled_data = scaler.transform(input_data)
        raw_score = float(model.decision_function(scaled_data)[0])
        return _decision_score_to_trust_score(raw_score)

    except (ValueError, KeyError, AttributeError, TypeError) as e:
        logger.error("Error predicting trust score: %s", e)
        raise MLModelUnavailableException(f"ML inference error: {e}") from e


def _decision_score_to_trust_score(decision_score: float) -> int:
    """Map the calibrated Isolation Forest decision score to 0-100."""
    scale = max(calibration_p_max - calibration_p_min, 1e-4)
    raw_trust = ((decision_score - calibration_p_min) / scale) * 100.0
    return max(0, min(100, round(raw_trust)))


def _fallback_trust_score(features: dict) -> int:
    """Legacy rule-based fallback retained for tests/backward compatibility."""
    dwell = features.get("avg_dwell_time_ms", 100.0)
    std_dwell = features.get("std_dwell_time_ms", 10.0)
    flight = features.get("avg_flight_time_ms", 150.0)
    std_flight = features.get("std_flight_time_ms", 15.0)

    score = 100.0
    if std_dwell <= 0.0 and std_flight <= 0.0:
        score -= 80.0
    if dwell < 40.0 or dwell > 400.0:
        score -= 30.0
    if flight < 10.0 or flight > 800.0:
        score -= 30.0
    return max(0, min(100, round(score)))
