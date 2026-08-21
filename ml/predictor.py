import json
import logging
import os

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# Base path for models
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "scaler.pkl")
CALIBRATION_PATH = os.path.join(BASE_DIR, "calibration.json")
METADATA_PATH = os.path.join(BASE_DIR, "model_metadata.json")


# Load model, scaler, and calibration parameters
model = None
scaler = None
calibration_p_min = -0.20
calibration_p_max = 0.10
feature_indices = [0, 1, 2, 4]


ACTIVE_MODEL_PATH = os.path.join(BASE_DIR, "artifacts", "production", "active_model.json")

def reload_model():
    """
    Hot-reloads model, scaler, empirical calibration parameters, and model metadata from disk.
    Guided by active_model.json activation metadata (Item 10).
    """
    global model, calibration_p_min, calibration_p_max, feature_indices

    if os.path.exists(ACTIVE_MODEL_PATH):
        try:
            with open(ACTIVE_MODEL_PATH, "r") as f:
                act = json.load(f)
                logger.info(f"✅ Active Model Registry: version='{act.get('active_version')}', activated_at='{act.get('activated_at')}', previous='{act.get('previous_version')}'")
        except (OSError, ValueError, KeyError) as e:
            logger.warning(f"Could not load active_model.json ({e}).")

    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        logger.info("✅ TrustGuard AI Mahalanobis reference model hot-reloaded successfully.")


    if os.path.exists(CALIBRATION_PATH):
        try:
            with open(CALIBRATION_PATH, "r") as f:
                cal_data = json.load(f)
                calibration_p_min = cal_data.get("p_min", -0.20)
                calibration_p_max = cal_data.get("p_max", 0.10)
                logger.info(f"✅ Empirical Calibration loaded: p_min={calibration_p_min:.4f}, p_max={calibration_p_max:.4f}")
        except (OSError, ValueError, KeyError) as e:
            logger.warning(f"Failed to load calibration parameters ({e}). Using defaults.")

    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r") as f:
                meta = json.load(f)
                feature_indices = meta.get("feature_indices", [0, 1, 2, 4])
                winning_arch = meta.get("winning_architecture", "Unknown")
                production_eer = meta.get("production_eer", 0.0)
                production_auc = meta.get("production_auc", 0.0)
                logger.info(f"✅ Promoted model metadata loaded: architecture='{winning_arch}', variant='{meta.get('winning_feature_variant')}', EER={production_eer}%, AUC={production_auc}")
        except (OSError, ValueError, KeyError) as e:

            logger.warning(f"Failed to load model metadata ({e}). Using defaults.")



try:
    reload_model()
except (OSError, FileNotFoundError, ValueError) as e:
    logger.error(f"❌ Failed to load ML model: {e}")


class MLModelUnavailableException(Exception):
    """Raised when the ML inference model or scaler is unavailable."""


def predict_trust_score(features: dict) -> int:
    """
    Predicts a trust score (0-100) based on extracted telemetry features using empirical percentile calibration.
    If the model is unavailable, raises MLModelUnavailableException to enforce fail-closed degraded authentication.
    """
    if model is None or scaler is None:
        logger.warning("[SECURITY DEGRADED] ML model or scaler unavailable. Enforcing fail-closed degraded mode.")
        raise MLModelUnavailableException("ML Inference model unavailable.")

    try:
        avg_d = float(features.get("avg_dwell_time_ms", 0.0))
        std_d = float(features.get("std_dwell_time_ms", 0.0))
        avg_f = float(features.get("avg_flight_time_ms", 0.0))
        std_f = float(features.get("std_flight_time_ms", 0.0))
        spd = float(features.get("typing_speed_cps", 0.0))
        df_ratio = avg_d / (avg_f + 1e-5)
        # Pause frequency (Point 1): Actual count/proportion of flight times > 200ms
        pause_freq = float(features.get("pause_count", 0))

        all_features = [avg_d, std_d, avg_f, std_f, spd, df_ratio, pause_freq]
        input_vector = [all_features[idx] for idx in feature_indices]
        input_data = np.array([input_vector])

        scaled_data = scaler.transform(input_data)
        raw_score = float(model.decision_function(scaled_data)[0])
        return _decision_score_to_trust_score(raw_score)

    except (ValueError, KeyError, AttributeError) as e:
        logger.error(f"Error predicting trust score: {e}")
        raise MLModelUnavailableException(f"ML Inference error: {e}")




def _decision_score_to_trust_score(decision_score: float) -> int:
    """
    Converts raw Isolation Forest decision_function score into a human-readable Trust Score (0 to 100)
    using empirical percentile bounds (p_min and p_max) saved during model training/evaluation.
    """
    scale = max(calibration_p_max - calibration_p_min, 1e-4)
    raw_trust = ((decision_score - calibration_p_min) / scale) * 100.0
    return max(0, min(100, round(raw_trust)))



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