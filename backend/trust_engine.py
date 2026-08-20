import logging
import math
from collections import Counter

from ml.predictor import predict_trust_score

logger = logging.getLogger(__name__)

BOT_STD_THRESHOLD = 2.0
AI_WEIGHT = 0.7
SIMILARITY_WEIGHT = 0.3
MIN_KEYSTROKES_FOR_BIOMETRICS = 5


def has_usable_biometric_signal(features: dict) -> bool:
    """
    Centralized definition of usable biometric signal across all system components.
    Requires at least MIN_KEYSTROKES_FOR_BIOMETRICS (5) AND non-zero dwell time.
    """
    if not features:
        return False
    keystroke_count = features.get("keystroke_count", 0)
    avg_dwell = features.get("avg_dwell_time_ms", 0.0)
    return keystroke_count >= MIN_KEYSTROKES_FOR_BIOMETRICS and avg_dwell > 0.0


ESCALATION_THRESHOLD = 3
DEESCALATION_THRESHOLD = 2
TRUST_THRESHOLD = 50


def calculate_shannon_entropy(val_list):
    """
    Computes Shannon entropy (in bits) of a list of timing values.
    Low entropy (< 0.5) indicates highly repetitive automated script signals.
    """
    if not val_list or len(val_list) < 2:
        return 1.0
    rounded = [round(v, 1) for v in val_list]
    counts = Counter(rounded)
    total = len(rounded)
    entropy = -sum((cnt / total) * math.log2(cnt / total) for cnt in counts.values())
    return entropy


def calculate_trust_score(
    features,
    similarity_score=100
):
    """
    Calculate the final trust score by combining:
    1. AI model prediction
    2. Behaviour profile similarity
    3. Shannon entropy and micro-variance bot checks
    """
    entropy_penalty = 1.0

    if has_usable_biometric_signal(features):
        std_dwell = features.get("std_dwell_time_ms", 0.0)
        std_flight = features.get("std_flight_time_ms", 0.0)
        avg_dwell = features.get("avg_dwell_time_ms", 0.0)
        avg_flight = features.get("avg_flight_time_ms", 0.0)

        if std_dwell < BOT_STD_THRESHOLD or std_flight < BOT_STD_THRESHOLD:
            logger.warning(f"[SECURITY ALERT] Synthetic bot detected! std_dwell={std_dwell:.2f}ms, std_flight={std_flight:.2f}ms")
            return 0.0

        # Calculate Shannon entropy over timing vector
        timing_vector = [avg_dwell, std_dwell, avg_flight, std_flight]
        entropy_val = calculate_shannon_entropy(timing_vector)
        if entropy_val < 0.5:
            entropy_penalty = max(0.5, entropy_val)
            logger.warning(f"[SECURITY ALERT] Low Shannon entropy detected: {entropy_val:.3f}")

    from ml.predictor import MLModelUnavailableException

    try:
        ai_score = predict_trust_score(features)
    except MLModelUnavailableException as e:
        logger.warning(f"[SECURITY DEGRADED] ML model unavailable ({e}). Enforcing fail-closed degraded score of 35.0.")
        ai_score = 35.0

    final_score = (
        ai_score * AI_WEIGHT +
        similarity_score * SIMILARITY_WEIGHT
    ) * entropy_penalty


    return round(final_score, 2)




def update_security_state(session: dict, trust_score: float, adaptive_threshold: float = TRUST_THRESHOLD) -> str:
    """
    Enforces security state transitions with hysteresis:
    NORMAL -> SUSPICIOUS -> HIGH_RISK -> LOCKED

    - Low-trust violations (trust_score < adaptive_threshold) increment low_trust_count.
    - 3 consecutive low-trust violations trigger state escalation.
    - 2 consecutive high-trust observations (trust_score >= adaptive_threshold) trigger de-escalation.
    - Bot detections (trust score == 0.0) trigger immediate LOCK.
    - LOCKED state requires manual override/reset and cannot recover.
    """
    current_state = session.get("security_state", "NORMAL")
    if current_state == "LOCKED":
        return "LOCKED"

    low_trust_count = session.get("low_trust_count", 0)
    high_trust_count = session.get("high_trust_count", 0)

    # Bot detection triggers immediate LOCK
    if trust_score <= 1e-6:
        session["security_state"] = "LOCKED"
        session["low_trust_count"] = 0
        session["high_trust_count"] = 0
        return "LOCKED"

    threshold = adaptive_threshold if adaptive_threshold is not None else TRUST_THRESHOLD

    if trust_score < threshold:
        low_trust_count += 1
        high_trust_count = 0
        
        if low_trust_count >= ESCALATION_THRESHOLD:
            old_state = current_state
            if current_state == "NORMAL":
                current_state = "SUSPICIOUS"
            elif current_state == "SUSPICIOUS":
                current_state = "HIGH_RISK"
            elif current_state == "HIGH_RISK":
                current_state = "LOCKED"
            low_trust_count = 0
            if current_state != old_state:
                session["step_up_completed"] = False
    else:
        high_trust_count += 1
        low_trust_count = 0
        
        if high_trust_count >= DEESCALATION_THRESHOLD:
            if current_state == "HIGH_RISK":
                current_state = "SUSPICIOUS"
            elif current_state == "SUSPICIOUS":
                current_state = "NORMAL"
                session["step_up_completed"] = False
            high_trust_count = 0

    session["security_state"] = current_state
    session["low_trust_count"] = low_trust_count
    session["high_trust_count"] = high_trust_count
    return current_state




def is_step_up_required(session: dict) -> bool:
    """
    Returns True if current security state requires Step-Up Re-Authentication challenge
    before de-escalating or escalating further.
    """
    state = session.get("security_state", "NORMAL")
    step_up_done = session.get("step_up_completed", False)
    return state in ("SUSPICIOUS", "HIGH_RISK") and not step_up_done