import os
import joblib
import numpy as np
import logging

logger = logging.getLogger(__name__)

# ======================================
# Constants
# ======================================

DECISION_SCORE_MIN = -0.20
DECISION_SCORE_MAX = 0.20
DECISION_SCORE_SCALE = 0.40

# ======================================
# Load Trained Model
# ======================================

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "saved_model",
    "trust_model.pkl"
)

model = joblib.load(MODEL_PATH)

try:
    logger.info("✅ TrustGuard AI model loaded successfully.")
except UnicodeEncodeError:
    logger.info("[SUCCESS] TrustGuard AI model loaded successfully.")


def reload_model() -> None:
    """
    Hot-swap the Isolation Forest model from disk without restarting the server.
    Called after a successful /admin/retrain to pick up the new artifact.
    """
    global model
    model = joblib.load(MODEL_PATH)
    logger.info("[PREDICTOR] Model hot-reloaded from disk after retraining.")




def predict_trust_score(features):
    """
    Predict a continuous trust score (0-100)
    using the real CMU-trained Isolation Forest model.
    """

    # --------------------------------------
    # Validate required features
    # --------------------------------------

    required = [
        "avg_dwell_time_ms",
        "avg_flight_time_ms",
        "typing_speed_cps"
    ]

    for key in required:
        if key not in features:
            raise ValueError(f"Missing feature: {key}")

    # --------------------------------------
    # Prepare feature vector
    # --------------------------------------

    sample = np.array([[
        float(features["avg_dwell_time_ms"]),
        float(features["avg_flight_time_ms"]),
        float(features["typing_speed_cps"])
    ]])

    # --------------------------------------
    # Predict
    # --------------------------------------

    decision_score = model.decision_function(sample)[0]

    # --------------------------------------
    # Convert decision score to trust score
    # --------------------------------------

    # Clamp score to a reasonable range
    decision_score = max(DECISION_SCORE_MIN, min(DECISION_SCORE_MAX, decision_score))

    # Scale to 0-100
    trust_score = ((decision_score - DECISION_SCORE_MIN) / DECISION_SCORE_SCALE) * 100

    trust_score = int(round(trust_score))

    # Keep inside limits
    trust_score = max(0, min(100, trust_score))

    # --------------------------------------
    # Debug Output
    # --------------------------------------

    logger.debug("\n================ Prediction ================")
    logger.debug(f"Dwell Time   : {sample[0][0]:.2f} ms")
    logger.debug(f"Flight Time  : {sample[0][1]:.2f} ms")
    logger.debug(f"Typing Speed : {sample[0][2]:.2f} cps")
    logger.debug("--------------------------------------------")
    logger.debug(f"Decision Score : {decision_score:.5f}")
    logger.debug(f"Trust Score    : {trust_score}")
    logger.debug("============================================\n")

    return trust_score